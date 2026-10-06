"""
=======================================================================
  FILE: traffic_simulator.py
  PROJECT: Network Intrusion Detection System (NIDS)
  STUDENT: Harsh Soam, Abhishek Arya
  TEACHER: Mr. Varun Chaudhary
=======================================================================

  WHAT IS THIS FILE?
  ------------------
  Since capturing REAL network packets requires administrator privileges
  and special libraries (like Scapy with WinPcap/Npcap on Windows),
  we BUILD A TRAFFIC SIMULATOR that generates realistic network packets.

  WHY SIMULATE INSTEAD OF CAPTURE REAL PACKETS?
  ----------------------------------------------
  1. No admin/root privileges needed (great for college labs!)
  2. We can trigger specific attack scenarios on demand
  3. We can test our detector works correctly
  4. Demo is predictable and educational
  5. Real-world NIDS logic is IDENTICAL — we just swap the source

  HOW THE SIMULATOR WORKS:
  ------------------------
  It creates a background thread that continuously generates
  fake network "packets" as Python dictionaries, mimicking real
  packet structures (source IP, destination IP, port, protocol, payload).

  In a real NIDS you would replace this with:
    → scapy: sniff(prn=process_packet, store=0)
    → pyshark: capture = pyshark.LiveCapture(interface='eth0')
=======================================================================
"""

import random
import time
import threading
import ipaddress
from datetime import datetime

# Import our signatures to generate realistic attack traffic
from signatures import ATTACK_SIGNATURES, SUSPICIOUS_PORTS


# =======================================================================
# CLASS: NetworkPacket
# =======================================================================
# WHAT IS IT?
#   A simple data container (like a struct in C) that represents
#   one network packet captured from the network.
#
# WHY A CLASS?
#   Real packets from Scapy are complex objects. By creating our own
#   class, our detector code works the same whether it's getting
#   real or simulated packets.
#
# KEY FIELDS EXPLAINED:
#   src_ip      = Where the packet came FROM (source)
#   dst_ip      = Where the packet is GOING TO (destination)
#   src_port    = Which "door" the sender used
#   dst_port    = Which "door" the receiver is at
#   protocol    = Language/rules used (TCP, UDP, ICMP, HTTP)
#   payload     = The actual data/message inside the packet
#   timestamp   = When was this packet seen
#   size        = How big is the packet (in bytes)
#   flags       = TCP control bits (SYN, ACK, FIN, RST)
# =======================================================================
class NetworkPacket:
    """Represents a single network packet (real or simulated)."""
    
    def __init__(self, src_ip, dst_ip, src_port, dst_port, 
                 protocol, payload="", size=64, flags=None):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.protocol = protocol
        self.payload = payload
        self.size = size
        self.flags = flags or []          # TCP flags: ['SYN'], ['SYN','ACK'], etc.
        self.timestamp = datetime.now()
        self.packet_id = random.randint(1000, 99999)  # Unique ID for tracking

    def __repr__(self):
        return (f"Packet[{self.protocol}] {self.src_ip}:{self.src_port} → "
                f"{self.dst_ip}:{self.dst_port} | Flags: {self.flags}")


# =======================================================================
# CLASS: TrafficSimulator
# =======================================================================
# WHAT IS IT?
#   Generates a continuous stream of fake but realistic network packets.
#   Some packets are NORMAL traffic, some are ATTACK traffic.
#
# HOW IT WORKS:
#   1. Runs in a background thread (so NIDS can process simultaneously)
#   2. Every 0.1-0.5 seconds, generates a new batch of packets
#   3. Random chance of generating attack traffic
#   4. Puts packets into a shared queue for the detector to process
# =======================================================================
class TrafficSimulator:
    """
    Simulates realistic network traffic including normal and attack patterns.
    
    HOW TO USE:
        simulator = TrafficSimulator()
        simulator.start()
        packets = simulator.get_packets()  # Get generated packets
        simulator.stop()
    """
    
    def __init__(self):
        self.running = False
        self.packets = []               # Buffer of generated packets
        self.packets_lock = threading.Lock()  # Thread-safe access
        self.thread = None
        
        # Statistics tracking
        self.total_generated = 0
        self.attack_packets_generated = 0
        
        # Attacker IPs (fixed set for realistic simulation)
        # In real life, attackers can spoof IP addresses!
        self.known_attacker_ips = [
            "192.168.1.100",    # Simulated internal attacker
            "10.0.0.50",        # Another internal threat
            "203.0.113.5",      # External attacker (RFC 5737 example range)
            "198.51.100.10",    # Another external attacker
            "185.220.101.1",    # Simulated Tor exit node
        ]
        
        # Legitimate user IPs
        self.legitimate_ips = [
            f"192.168.1.{i}" for i in range(1, 20)  # Local network users
        ] + [
            "8.8.8.8",          # Google DNS
            "142.250.80.14",    # Google server
            "13.107.42.14",     # Microsoft server
        ]
        
        # Our server's IP (the target being protected)
        self.server_ip = "192.168.1.10"
        self.server_ports = [80, 443, 22, 21, 3306, 8080]  # Running services

    def start(self):
        """Start the traffic generation in background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._generate_traffic, daemon=True)
        self.thread.start()
        print("[SIMULATOR] Traffic simulation STARTED")

    def stop(self):
        """Stop the traffic generator."""
        self.running = False
        print("[SIMULATOR] Traffic simulation STOPPED")

    def get_packets(self, max_packets=50):
        """
        Thread-safely retrieve generated packets.
        
        WHY THREAD-SAFE?
        The simulator runs in Thread A, the detector reads in Thread B.
        Without locks, both might access 'packets' list simultaneously
        causing data corruption (Race Condition!).
        'threading.Lock()' ensures only ONE thread accesses at a time.
        """
        with self.packets_lock:
            if not self.packets:
                return []
            # Take up to max_packets and clear the buffer
            retrieved = self.packets[:max_packets]
            self.packets = self.packets[max_packets:]
            return retrieved

    # -------------------------------------------------------------------
    # PRIVATE METHODS: Traffic Generation
    # -------------------------------------------------------------------
    # The underscore prefix (_) in Python means "private" (by convention)
    # These are internal implementation details, not public API
    # -------------------------------------------------------------------

    def _generate_traffic(self):
        """
        Main loop running in background thread.
        
        HOW IT DECIDES WHAT TO GENERATE:
        Using weighted random selection:
          - 60% normal traffic (browsing, file transfers)
          - 15% port scan attack
          - 12% brute force attempt  
          - 8%  SQL injection
          - 5%  DoS/SYN flood
          - etc.
        """
        attack_scenarios = [
            (self._normal_http_traffic, 30),      # 30 weight = 30% chance
            (self._normal_dns_traffic, 15),
            (self._normal_ssh_traffic, 10),
            (self._port_scan_attack, 15),          # Attack scenarios
            (self._brute_force_attack, 12),
            (self._sql_injection_attack, 8),
            (self._syn_flood_attack, 5),
            (self._icmp_flood_attack, 3),
            (self._xss_attack, 2),
        ]
        
        # Separate weights for random.choices()
        scenarios = [s[0] for s in attack_scenarios]
        weights = [s[1] for s in attack_scenarios]
        
        while self.running:
            # Pick a traffic type randomly (weighted)
            chosen_scenario = random.choices(scenarios, weights=weights, k=1)[0]
            
            # Generate packets for that scenario
            new_packets = chosen_scenario()
            
            # Safely add to shared buffer
            with self.packets_lock:
                self.packets.extend(new_packets)
                self.total_generated += len(new_packets)
            
            # Wait before next burst (simulates real traffic timing)
            time.sleep(random.uniform(0.05, 0.3))

    # -------------------------------------------------------------------
    # NORMAL TRAFFIC GENERATORS
    # -------------------------------------------------------------------

    def _normal_http_traffic(self):
        """Generate normal web browsing traffic (HTTP/HTTPS)."""
        packets = []
        user_ip = random.choice(self.legitimate_ips[:10])  # Local users
        
        # HTTP GET request
        http_methods = ["GET", "POST", "PUT"]
        paths = ["/index.html", "/login", "/about", "/api/data", "/images/logo.png"]
        
        packets.append(NetworkPacket(
            src_ip=user_ip,
            dst_ip=self.server_ip,
            src_port=random.randint(1024, 65535),
            dst_port=random.choice([80, 443, 8080]),
            protocol="HTTP",
            payload=f"{random.choice(http_methods)} {random.choice(paths)} HTTP/1.1",
            size=random.randint(64, 1500),
            flags=["SYN"] if random.random() < 0.3 else ["ACK"]
        ))
        return packets

    def _normal_dns_traffic(self):
        """Generate normal DNS lookup traffic."""
        domains = ["google.com", "youtube.com", "github.com", "microsoft.com"]
        user_ip = random.choice(self.legitimate_ips[:10])
        
        return [NetworkPacket(
            src_ip=user_ip,
            dst_ip="8.8.8.8",          # Google DNS server
            src_port=random.randint(1024, 65535),
            dst_port=53,               # DNS port is always 53
            protocol="DNS",
            payload=f"Query: {random.choice(domains)}",
            size=random.randint(40, 100),
        )]

    def _normal_ssh_traffic(self):
        """Generate normal SSH connection traffic."""
        admin_ips = ["192.168.1.2", "192.168.1.3"]  # Known admins
        
        return [NetworkPacket(
            src_ip=random.choice(admin_ips),
            dst_ip=self.server_ip,
            src_port=random.randint(1024, 65535),
            dst_port=22,               # SSH always on port 22
            protocol="TCP",
            payload="SSH-2.0-OpenSSH_8.0",  # Normal SSH banner
            size=random.randint(100, 400),
            flags=["ACK"]
        )]

    # -------------------------------------------------------------------
    # ATTACK TRAFFIC GENERATORS
    # -------------------------------------------------------------------

    def _get_attacker_ip(self):
        """
        Returns an attacker IP.
        Mixes known repeat offenders with dynamic external internet IPs
        so the simulation continuously generates fresh attacks even after some IPs are auto-blocked.
        """
        if random.random() < 0.35:
            return random.choice(self.known_attacker_ips)
        prefix = random.choice([45, 91, 103, 114, 142, 178, 185, 194, 198, 203, 212])
        return f"{prefix}.{random.randint(10, 240)}.{random.randint(1, 254)}.{random.randint(2, 254)}"

    def _port_scan_attack(self):
        """
        Simulate a PORT SCAN attack.
        
        HOW A REAL PORT SCAN WORKS:
        Tool like nmap sends SYN packets to every port (0-65535).
        If port is OPEN → gets SYN-ACK back.
        If port is CLOSED → gets RST back.
        
        We simulate this by generating many packets from one IP
        to many different destination ports quickly.
        """
        attacker_ip = self._get_attacker_ip()
        packets = []
        
        # Scan a random range of ports
        ports_to_scan = random.sample(range(1, 1024), random.randint(15, 30))
        
        for port in ports_to_scan:
            packets.append(NetworkPacket(
                src_ip=attacker_ip,
                dst_ip=self.server_ip,
                src_port=random.randint(40000, 65535),  # Random high source port
                dst_port=port,
                protocol="TCP",
                payload="",             # Port scans have empty payloads
                size=44,                # Minimum TCP packet size
                flags=["SYN"]           # Only SYN — attacker never completes handshake
            ))
        
        self.attack_packets_generated += len(packets)
        return packets

    def _syn_flood_attack(self):
        """
        Simulate SYN FLOOD (Denial of Service) attack.
        
        HOW IT WORKS:
        Send thousands of TCP SYN packets with SPOOFED source IPs.
        Server allocates memory for each half-open connection.
        When memory is full → legitimate users can't connect.
        
        KEY IDENTIFIER: Many SYN packets, many different IPs, same destination.
        """
        packets = []
        target_port = random.choice([80, 443, 22])
        
        # Generate a burst of SYN packets with spoofed/random IPs
        for _ in range(random.randint(80, 150)):
            # Spoofed source IPs (attacker hides real location)
            fake_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
            
            packets.append(NetworkPacket(
                src_ip=fake_ip,
                dst_ip=self.server_ip,
                src_port=random.randint(1024, 65535),
                dst_port=target_port,
                protocol="TCP",
                payload="",
                size=44,
                flags=["SYN"]           # ONLY SYN, never ACK (that's the attack!)
            ))
        
        self.attack_packets_generated += len(packets)
        return packets

    def _sql_injection_attack(self):
        """
        Simulate SQL Injection attack via HTTP.
        """
        attacker_ip = self._get_attacker_ip()
        
        # Real SQL injection payloads used by attackers
        sql_payloads = [
            "SELECT * FROM users WHERE username='' OR '1'='1",
            "'; DROP TABLE users; --",
            "UNION SELECT username, password FROM admin--",
            "1' AND SLEEP(5)--",        # Time-based blind SQL injection
            "admin'--",
            "' OR 1=1--",
            "'; EXEC xp_cmdshell('whoami')--",    # Command execution via SQL!
            "' WAITFOR DELAY '0:0:5'--",
            "1 UNION SELECT NULL,NULL,NULL--",
        ]
        
        return [NetworkPacket(
            src_ip=attacker_ip,
            dst_ip=self.server_ip,
            src_port=random.randint(1024, 65535),
            dst_port=80,
            protocol="HTTP",
            payload=f"POST /login HTTP/1.1\r\nContent: {random.choice(sql_payloads)}",
            size=random.randint(100, 500),
            flags=["ACK"]
        )]

    def _brute_force_attack(self):
        """
        Simulate BRUTE FORCE login attack.
        """
        attacker_ip = self._get_attacker_ip()
        packets = []
        
        # Target service (SSH and FTP are most commonly brute-forced)
        target_port = random.choice([22, 21, 3306])
        
        common_passwords = [
            "password", "123456", "admin", "root", "letmein",
            "qwerty", "abc123", "monkey", "1234567", "pass"
        ]
        usernames = ["admin", "root", "administrator", "user", "test"]
        
        # Generate multiple rapid login attempts
        for _ in range(random.randint(6, 15)):
            packets.append(NetworkPacket(
                src_ip=attacker_ip,
                dst_ip=self.server_ip,
                src_port=random.randint(40000, 65535),
                dst_port=target_port,
                protocol="TCP",
                payload=f"AUTH {random.choice(usernames)}:{random.choice(common_passwords)}",
                size=random.randint(80, 200),
                flags=["PSH", "ACK"]
            ))
        
        self.attack_packets_generated += len(packets)
        return packets

    def _icmp_flood_attack(self):
        """
        Simulate ICMP FLOOD (Ping Flood) attack.
        """
        attacker_ip = self._get_attacker_ip()
        packets = []
        
        for _ in range(random.randint(60, 100)):
            packets.append(NetworkPacket(
                src_ip=attacker_ip,
                dst_ip=self.server_ip,
                src_port=0,
                dst_port=0,
                protocol="ICMP",
                payload="ECHO_REQUEST",
                size=random.randint(1000, 65507),
            ))
        
        self.attack_packets_generated += len(packets)
        return packets

    def _xss_attack(self):
        """
        Simulate Cross-Site Scripting (XSS) attack.
        """
        attacker_ip = self._get_attacker_ip()
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(document.cookie)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
            "';alert('xss')//",
            "<iframe src='javascript:alert(1)'></iframe>",
        ]
        
        return [NetworkPacket(
            src_ip=attacker_ip,
            dst_ip=self.server_ip,
            src_port=random.randint(1024, 65535),
            dst_port=80,
            protocol="HTTP",
            payload=f"GET /search?q={random.choice(xss_payloads)} HTTP/1.1",
            size=random.randint(100, 400),
            flags=["ACK"]
        )]
