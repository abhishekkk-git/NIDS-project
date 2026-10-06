"""
=======================================================================
  FILE: detector.py
  PROJECT: Network Intrusion Detection System (NIDS)
  STUDENT: Harsh Soam, Abhishek Arya
  TEACHER: Mr. Varun Chaudhary
=======================================================================

  WHAT IS THIS FILE?
  ------------------
  This is the CORE ENGINE of our NIDS. This is where all the magic
  happens! The detector:
    1. Receives packets from the simulator (or real network)
    2. Runs each packet through detection algorithms
    3. Generates alerts when attacks are detected
    4. Maintains statistics for the dashboard

  KEY CONCEPTS USED:
  ------------------
  a) SLIDING WINDOW ALGORITHM:
     We track activity over a time window (e.g., last 5 seconds).
     We use Python's 'collections.deque' with a maxlen for efficiency.
     
  b) PATTERN MATCHING:
     For payload-based attacks (SQL injection, XSS), we scan the
     packet payload for known malicious strings.
     
  c) STATEFUL TRACKING:
     We remember which IP did what, for how long, using dictionaries.
     This is called "stateful inspection" (vs "stateless").
     
  d) THRESHOLD-BASED DETECTION:
     If a metric exceeds a threshold → alert.
     Example: >10 ports from same IP in 5 seconds → Port Scan!

  TYPES OF IDS:
  -------------
  1. SIGNATURE-BASED: Match against known patterns (like antivirus)
     → Fast, low false positives, can't detect new attacks (zero-days)
  2. ANOMALY-BASED: Learn "normal" behavior, flag deviations
     → Can detect zero-days, more false positives
  
  Our NIDS uses SIGNATURE-BASED detection (simpler, educational).
=======================================================================
"""

import time
import threading
from collections import defaultdict, deque
from datetime import datetime
import random

from signatures import ATTACK_SIGNATURES, SUSPICIOUS_PORTS


# =======================================================================
# CLASS: Alert
# =======================================================================
# When an attack is detected, we create an Alert object.
# This stores all information about the detected threat.
# =======================================================================
class Alert:
    """Represents a detected security threat/intrusion."""
    
    # Class variable — counts total alerts across all instances
    _alert_counter = 0
    
    def __init__(self, attack_type, packet, details, severity):
        Alert._alert_counter += 1
        self.alert_id = Alert._alert_counter
        self.attack_type = attack_type                           # e.g., "PORT_SCAN"
        self.attack_name = ATTACK_SIGNATURES[attack_type]["name"] if attack_type in ATTACK_SIGNATURES else attack_type
        self.src_ip = packet.src_ip
        self.dst_ip = packet.dst_ip
        self.dst_port = packet.dst_port
        self.protocol = packet.protocol
        self.details = details                                   # Human-readable explanation
        self.severity = severity
        self.timestamp = datetime.now()
        self.time_str = self.timestamp.strftime("%H:%M:%S")
        
        # Get prevention advice from signatures database
        sig = ATTACK_SIGNATURES.get(attack_type, {})
        self.prevention = sig.get("how_to_prevent", "Monitor and investigate")
        self.icon = sig.get("icon", "⚠️")
        self.color = sig.get("color", "#e74c3c")

    def to_dict(self):
        """Convert alert to dictionary (for JSON serialization to dashboard)."""
        return {
            "alert_id": self.alert_id,
            "attack_type": self.attack_type,
            "attack_name": self.attack_name,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "details": self.details,
            "severity": self.severity,
            "timestamp": self.time_str,
            "prevention": self.prevention,
            "icon": self.icon,
            "color": self.color,
        }


# =======================================================================
# CLASS: IntrusionDetector
# =======================================================================
# THE MAIN DETECTION ENGINE
#
# ARCHITECTURE:
#   The detector maintains several "tracking tables" — dictionaries
#   that store recent activity per IP address.
#
#   When a new packet arrives:
#   1. Update all tracking tables with packet info
#   2. Run each detector function
#   3. If any detector fires → create Alert
#   4. Store alert in alerts list
# =======================================================================
class IntrusionDetector:
    """
    Core NIDS engine implementing multiple attack detection algorithms.
    
    USAGE:
        detector = IntrusionDetector()
        alert = detector.analyze_packet(packet)
        if alert:
            print(f"ALERT: {alert.attack_name}")
    """
    
    def __init__(self):
        # -----------------------------------------------------------
        # TRACKING TABLES
        # -----------------------------------------------------------
        # WHY defaultdict?
        #   defaultdict auto-creates a default value when a new key
        #   is accessed. So we don't need to check "if ip in dict".
        #
        # WHY deque(maxlen=X)?
        #   deque is a double-ended queue. When maxlen is set and deque
        #   is full, oldest items are automatically dropped.
        #   This implements our "sliding time window"!
        # -----------------------------------------------------------
        
        # Track which ports each IP has tried to connect to
        # {ip: deque([port1, port2, port3, ...])}
        self.port_scan_tracker = defaultdict(lambda: deque(maxlen=200))
        
        # Track SYN packets per second per IP (for SYN flood detection)
        # {ip: deque([timestamp1, timestamp2, ...])}
        self.syn_tracker = defaultdict(lambda: deque(maxlen=1000))
        
        # Track login attempts per IP (for brute force detection)
        # {ip: deque([timestamp1, timestamp2, ...])}
        self.brute_force_tracker = defaultdict(lambda: deque(maxlen=100))
        
        # Track ICMP packets per IP (for ICMP flood detection)
        # {ip: deque([timestamp1, timestamp2, ...])}
        self.icmp_tracker = defaultdict(lambda: deque(maxlen=500))
        
        # Store all generated alerts
        self.alerts = []
        self.alerts_lock = threading.Lock()
        
        # Store recently seen IPs to prevent duplicate alerts
        # (don't alert same attack from same IP more than once per 10 seconds)
        self.alert_cooldown = {}  # {(ip, attack_type): last_alert_time}
        self.cooldown_period = 8  # seconds
        
        # Statistics counters
        self.stats = {
            "total_packets": 0,
            "total_alerts": 0,
            "packets_per_second": 0,
            "attack_counts": defaultdict(int),
            "top_attackers": defaultdict(int),
            "severity_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            "protocol_counts": defaultdict(int),
            "blocked_ips": set(),
        }
        
        # For PPS (packets per second) calculation
        self._recent_packet_times = deque(maxlen=1000)
        
        print("[DETECTOR] Intrusion Detection Engine initialized")
        print(f"[DETECTOR] Loaded {len(ATTACK_SIGNATURES)} attack signatures")

    # ===================================================================
    # MAIN ANALYSIS FUNCTION
    # ===================================================================
    def analyze_packet(self, packet):
        """
        Analyze a single packet for intrusion indicators.
        
        ALGORITHM:
        1. Update statistics
        2. Run through all detectors
        3. Return first alert found (or None if clean)
        
        WHY RETURN ONLY FIRST?
        In production NIDS, all alerts are returned. For our demo,
        we return one to keep things simple and readable.
        
        Args:
            packet: NetworkPacket object
        Returns:
            Alert object if attack detected, None otherwise
        """
        # Step 1: Update global statistics
        self._update_stats(packet)
        
        # Step 2: Check if this IP is already blocked (skip deeper analysis)
        if packet.src_ip in self.stats["blocked_ips"]:
            # Still count the packet but don't re-alert
            return None
        
        # Step 3: Run all detection algorithms
        # Each returns an Alert or None
        detectors = [
            self._detect_port_scan,
            self._detect_syn_flood,
            self._detect_sql_injection,
            self._detect_brute_force,
            self._detect_icmp_flood,
            self._detect_xss,
            self._detect_suspicious_port,
        ]
        
        for detector_func in detectors:
            alert = detector_func(packet)
            if alert:
                # Step 4: Check cooldown (don't spam same alert)
                if not self._is_in_cooldown(packet.src_ip, alert.attack_type):
                    self._record_alert(alert)
                    return alert
        
        return None  # No attack detected → clean packet

    # ===================================================================
    # DETECTOR 1: PORT SCAN DETECTION
    # ===================================================================
    def _detect_port_scan(self, packet):
        """
        Detects port scanning activity.
        
        ALGORITHM:
        1. For each source IP, track which destination ports it has accessed
        2. If unique ports > threshold within time window → Port Scan!
        
        WHY TRACK UNIQUE PORTS?
        Normal users connect to a few ports (80, 443, 22).
        Scanners hit dozens or hundreds of ports systematically.
        
        DATA STRUCTURE:
        port_scan_tracker[src_ip] = deque of (timestamp, port) tuples
        """
        current_time = time.time()
        src_ip = packet.src_ip
        
        # Record this port access with timestamp
        self.port_scan_tracker[src_ip].append((current_time, packet.dst_port))
        
        # Look at the time window (last N seconds)
        time_window = ATTACK_SIGNATURES["PORT_SCAN"]["time_window"]
        threshold = ATTACK_SIGNATURES["PORT_SCAN"]["threshold_ports"]
        
        # Filter: only consider accesses within the time window
        recent_accesses = [
            (t, p) for t, p in self.port_scan_tracker[src_ip]
            if current_time - t <= time_window
        ]
        
        # Count UNIQUE ports (a scanner hits each port once)
        unique_ports = len(set(p for _, p in recent_accesses))
        
        if unique_ports >= threshold:
            # IT'S A PORT SCAN!
            port_list = sorted(set(p for _, p in recent_accesses))
            return Alert(
                attack_type="PORT_SCAN",
                packet=packet,
                details=(f"Source {src_ip} scanned {unique_ports} unique ports "
                        f"in {time_window}s! Ports: {port_list[:10]}..."),
                severity="HIGH"
            )
        return None

    # ===================================================================
    # DETECTOR 2: SYN FLOOD DETECTION
    # ===================================================================
    def _detect_syn_flood(self, packet):
        """
        Detects TCP SYN Flood DoS attacks.
        
        ALGORITHM:
        1. Only process TCP packets with SYN flag
        2. Track SYN count per source IP per second
        3. If count > threshold → SYN Flood detected!
        
        THE TCP HANDSHAKE (3-way):
        Client → Server: SYN       (I want to connect)
        Server → Client: SYN-ACK   (OK, I'm ready)
        Client → Server: ACK       (Connection established)
        
        In SYN Flood: Client sends SYN but never sends ACK.
        Server keeps a "half-open" connection waiting → memory leak!
        """
        # Only care about TCP SYN packets
        if packet.protocol != "TCP" or "SYN" not in packet.flags:
            return None
        
        current_time = time.time()
        src_ip = packet.src_ip
        
        # Record this SYN with timestamp
        self.syn_tracker[src_ip].append(current_time)
        
        time_window = ATTACK_SIGNATURES["SYN_FLOOD"]["time_window"]
        threshold = ATTACK_SIGNATURES["SYN_FLOOD"]["threshold_packets"]
        
        # Count SYN packets in the last second
        recent_syns = sum(
            1 for t in self.syn_tracker[src_ip]
            if current_time - t <= time_window
        )
        
        if recent_syns >= threshold:
            return Alert(
                attack_type="SYN_FLOOD",
                packet=packet,
                details=(f"SYN Flood from {src_ip}: {recent_syns} SYN packets "
                        f"in {time_window}s to port {packet.dst_port}! "
                        f"Server may run out of connections."),
                severity="CRITICAL"
            )
        return None

    # ===================================================================
    # DETECTOR 3: SQL INJECTION DETECTION
    # ===================================================================
    def _detect_sql_injection(self, packet):
        """
        Detects SQL Injection attempts in HTTP payloads.
        
        ALGORITHM: Simple Pattern Matching
        1. Only check HTTP packets (port 80/443/8080)
        2. Convert payload to uppercase (case-insensitive search)
        3. Check if any SQL keyword is in the payload
        4. If yes → SQL Injection detected!
        
        WHY UPPERCASE?
        Attackers try to evade detection by mixing case:
        "SeLeCt * fRoM uSeRs"
        Converting both sides to uppercase normalizes this.
        
        LIMITATION:
        Simple pattern matching → false positives possible.
        Real NIDS uses regex with context awareness.
        """
        if packet.protocol not in ["HTTP", "HTTPS"]:
            return None
        
        if not packet.payload:
            return None
        
        payload_upper = packet.payload.upper()
        patterns = ATTACK_SIGNATURES["SQL_INJECTION"]["patterns"]
        
        for pattern in patterns:
            if pattern.upper() in payload_upper:
                return Alert(
                    attack_type="SQL_INJECTION",
                    packet=packet,
                    details=(f"SQL Injection attempt from {packet.src_ip}! "
                            f"Malicious pattern '{pattern}' found in payload. "
                            f"Payload: {packet.payload[:100]}..."),
                    severity="CRITICAL"
                )
        return None

    # ===================================================================
    # DETECTOR 4: BRUTE FORCE DETECTION
    # ===================================================================
    def _detect_brute_force(self, packet):
        """
        Detects brute force login attacks.
        
        ALGORITHM:
        1. Track connections to auth-related ports (22=SSH, 21=FTP, etc.)
        2. If too many attempts from same IP in time window → Brute Force!
        
        TARGET PORTS (authentication services):
        22   → SSH (Secure Shell) - remote server access
        21   → FTP (File Transfer Protocol)
        3306 → MySQL database
        3389 → RDP (Remote Desktop Protocol) - Windows remote access
        23   → Telnet (old, insecure remote access)
        
        REAL WORLD NOTE:
        Better detection checks for failed logins specifically.
        We check port access count as a simplification.
        """
        target_ports = ATTACK_SIGNATURES["BRUTE_FORCE"]["target_ports"]
        
        if packet.dst_port not in target_ports:
            return None
        
        current_time = time.time()
        src_ip = packet.src_ip
        
        # Record this login attempt
        self.brute_force_tracker[src_ip].append(current_time)
        
        time_window = ATTACK_SIGNATURES["BRUTE_FORCE"]["time_window"]
        threshold = ATTACK_SIGNATURES["BRUTE_FORCE"]["threshold_attempts"]
        
        # Count recent attempts
        recent_attempts = sum(
            1 for t in self.brute_force_tracker[src_ip]
            if current_time - t <= time_window
        )
        
        if recent_attempts >= threshold:
            port_names = {22: "SSH", 21: "FTP", 3306: "MySQL", 3389: "RDP", 23: "Telnet"}
            service = port_names.get(packet.dst_port, f"Port {packet.dst_port}")
            
            return Alert(
                attack_type="BRUTE_FORCE",
                packet=packet,
                details=(f"Brute Force on {service} from {src_ip}: "
                        f"{recent_attempts} login attempts in {time_window}s! "
                        f"Possible automated password guessing tool."),
                severity="HIGH"
            )
        return None

    # ===================================================================
    # DETECTOR 5: ICMP FLOOD DETECTION
    # ===================================================================
    def _detect_icmp_flood(self, packet):
        """
        Detects ICMP Flood / Ping of Death attacks.
        
        ALGORITHM:
        1. Only process ICMP packets
        2. Count ICMP packets from same IP per second
        3. If count > threshold → ICMP Flood!
        
        EXTRA CHECK: Packet size
        Normal pings are 32-64 bytes.
        "Ping of Death" uses oversized packets (>65507 bytes for IPv4).
        We flag both excessive count AND unusual size.
        """
        if packet.protocol != "ICMP":
            return None
        
        current_time = time.time()
        src_ip = packet.src_ip
        
        self.icmp_tracker[src_ip].append(current_time)
        
        time_window = ATTACK_SIGNATURES["ICMP_FLOOD"]["time_window"]
        threshold = ATTACK_SIGNATURES["ICMP_FLOOD"]["threshold_packets"]
        
        recent_icmp = sum(
            1 for t in self.icmp_tracker[src_ip]
            if current_time - t <= time_window
        )
        
        if recent_icmp >= threshold:
            # Check for oversized packets (Ping of Death signature)
            is_oversized = packet.size > 1500  # Standard MTU is 1500 bytes
            attack_variant = "Ping of Death" if is_oversized else "ICMP Flood"
            
            return Alert(
                attack_type="ICMP_FLOOD",
                packet=packet,
                details=(f"{attack_variant} from {src_ip}: {recent_icmp} ICMP "
                        f"packets in {time_window}s! Packet size: {packet.size} bytes. "
                        f"{'OVERSIZED PACKET DETECTED!' if is_oversized else ''}"),
                severity="MEDIUM"
            )
        return None

    # ===================================================================
    # DETECTOR 6: XSS DETECTION
    # ===================================================================
    def _detect_xss(self, packet):
        """
        Detects Cross-Site Scripting (XSS) injection attempts.
        
        Similar to SQL injection detection but looks for HTML/JS patterns.
        
        TYPES OF XSS:
        1. Stored XSS: Malicious script saved to database, affects all users
        2. Reflected XSS: Script in URL, affects only current user  
        3. DOM-based XSS: Client-side JavaScript manipulation
        
        ALGORITHM:
        Pattern matching on HTTP payloads for HTML/JS injection markers.
        """
        if packet.protocol not in ["HTTP", "HTTPS"]:
            return None
        
        if not packet.payload:
            return None
        
        payload_lower = packet.payload.lower()
        patterns = ATTACK_SIGNATURES["XSS"]["patterns"]
        
        for pattern in patterns:
            if pattern.lower() in payload_lower:
                return Alert(
                    attack_type="XSS",
                    packet=packet,
                    details=(f"XSS attempt from {packet.src_ip}! "
                            f"Malicious JavaScript pattern '{pattern}' found. "
                            f"Possible cookie theft or page hijacking attempt."),
                    severity="HIGH"
                )
        return None

    # ===================================================================
    # DETECTOR 7: SUSPICIOUS PORT ACCESS
    # ===================================================================
    def _detect_suspicious_port(self, packet):
        """
        Detects connections to well-known malicious/backdoor ports.
        
        WHY?
        Certain ports are almost exclusively used by malware, trojans,
        or hacking tools. Normal traffic never uses these ports.
        
        If we see traffic to/from these ports → high suspicion!
        """
        if packet.dst_port in SUSPICIOUS_PORTS:
            reason = SUSPICIOUS_PORTS[packet.dst_port]
            return Alert(
                attack_type="PORT_SCAN",   # Categorized under port scan for simplicity
                packet=packet,
                details=(f"Connection to suspicious port {packet.dst_port} "
                        f"from {packet.src_ip}! "
                        f"Known association: {reason}"),
                severity="MEDIUM"
            )
        return None

    # ===================================================================
    # HELPER METHODS
    # ===================================================================

    def _update_stats(self, packet):
        """Update global statistics with each packet processed."""
        self.stats["total_packets"] += 1
        self.stats["protocol_counts"][packet.protocol] += 1
        self.stats["top_attackers"][packet.src_ip] += 1
        
        # Track for PPS calculation
        self._recent_packet_times.append(time.time())
        
        # Calculate packets per second (packets in last 1 second)
        current_time = time.time()
        self.stats["packets_per_second"] = sum(
            1 for t in self._recent_packet_times
            if current_time - t <= 1.0
        )

    def _is_in_cooldown(self, src_ip, attack_type):
        """
        Check if we recently alerted for this IP/attack combo.
        
        WHY COOLDOWN?
        Without cooldown, a port scan generating 100 packets would
        trigger 100 identical alerts → alert fatigue!
        Security teams would start ignoring alerts (they actually do this
        in real organizations — it's called "alert fatigue").
        """
        key = (src_ip, attack_type)
        last_alert_time = self.alert_cooldown.get(key, 0)
        
        if time.time() - last_alert_time < self.cooldown_period:
            return True  # In cooldown — suppress duplicate alert
        
        # Update cooldown timer
        self.alert_cooldown[key] = time.time()
        return False

    def _record_alert(self, alert):
        """Save alert and update statistics."""
        with self.alerts_lock:
            self.alerts.append(alert)
            # Keep only last 100 alerts (memory management)
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
        
        self.stats["total_alerts"] += 1
        self.stats["attack_counts"][alert.attack_type] += 1
        self.stats["severity_counts"][alert.severity] += 1
        
        # Track attackers
        if alert.severity in ["HIGH", "CRITICAL"]:
            self.stats["top_attackers"][alert.src_ip] += 10  # Weight high-severity
        
        # Auto-block IPs with CRITICAL attacks
        if alert.severity == "CRITICAL":
            self.stats["blocked_ips"].add(alert.src_ip)

    def get_recent_alerts(self, count=20):
        """Get the most recent alerts (thread-safe)."""
        with self.alerts_lock:
            return [a.to_dict() for a in reversed(self.alerts[-count:])]

    def get_stats(self):
        """Return current statistics for dashboard."""
        return {
            "total_packets": self.stats["total_packets"],
            "total_alerts": self.stats["total_alerts"],
            "packets_per_second": self.stats["packets_per_second"],
            "attack_counts": dict(self.stats["attack_counts"]),
            "protocol_counts": dict(self.stats["protocol_counts"]),
            "severity_counts": dict(self.stats["severity_counts"]),
            "blocked_ips": list(self.stats["blocked_ips"]),
            "blocked_count": len(self.stats["blocked_ips"]),
            "top_attackers": sorted(
                self.stats["top_attackers"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
        }
