"""
=======================================================================
  FILE: signatures.py
  PROJECT: Network Intrusion Detection System (NIDS)
  SUBJECT: Computer Networks / Cyber Security Mini Project
  STUDENT: Harsh Soam, Abhishek Arya
  TEACHER: Mr. Varun Chaudhary
=======================================================================

  WHAT IS THIS FILE?
  ------------------
  This file acts as the "brain's memory" of our NIDS.
  Just like an antivirus has a virus database, our NIDS has
  a SIGNATURES DATABASE — a list of known attack patterns.

  WHY DO WE NEED SIGNATURES?
  ---------------------------
  When a criminal breaks into a house, they leave fingerprints.
  Similarly, cyber attacks leave "fingerprints" in network traffic.
  These fingerprints = SIGNATURES.

  HOW DOES IT WORK?
  ------------------
  We store patterns like:
    - Port numbers used by attackers
    - Suspicious keywords in HTTP requests
    - Thresholds that indicate flooding attacks
  Then we compare live traffic against these patterns.
=======================================================================
"""

# =======================================================================
# ATTACK SIGNATURES DICTIONARY
# =======================================================================
# Think of this as a "Most Wanted List" for network attacks.
# Each entry describes ONE TYPE of attack with its characteristics.
# =======================================================================

ATTACK_SIGNATURES = {

    # -------------------------------------------------------------------
    # 1. PORT SCAN DETECTION
    # -------------------------------------------------------------------
    # WHAT IS A PORT SCAN?
    #   An attacker probes multiple ports on your computer to find
    #   which services are running (like knocking on every door to
    #   see which one opens).
    #
    # HOW WE DETECT IT:
    #   If one IP tries to connect to many different ports in a short
    #   time, that's suspicious!
    # -------------------------------------------------------------------
    "PORT_SCAN": {
        "name": "Port Scan Attack",
        "description": "Attacker probing multiple ports to find open services",
        "severity": "HIGH",
        "threshold_ports": 10,        # If > 10 different ports hit from 1 IP → Alert!
        "time_window": 5,             # Within 5 seconds
        "color": "#e74c3c",
        "icon": "🔍",
        "how_to_prevent": "Use firewalls, disable unused ports, use port knocking"
    },

    # -------------------------------------------------------------------
    # 2. SYN FLOOD (DoS) DETECTION
    # -------------------------------------------------------------------
    # WHAT IS SYN FLOOD?
    #   In TCP connections, a client sends SYN → server replies SYN-ACK
    #   → client should reply ACK.
    #   In SYN Flood, attacker sends THOUSANDS of SYN but never ACK.
    #   Server runs out of memory waiting for ACKs → CRASH!
    #
    # HOW WE DETECT IT:
    #   Too many SYN packets from one IP in a short time window.
    # -------------------------------------------------------------------
    "SYN_FLOOD": {
        "name": "SYN Flood (DoS Attack)",
        "description": "Attacker overwhelming server with TCP SYN requests",
        "severity": "CRITICAL",
        "threshold_packets": 100,     # If > 100 SYN packets per second → Alert!
        "time_window": 1,
        "color": "#c0392b",
        "icon": "🌊",
        "how_to_prevent": "SYN cookies, rate limiting, firewall rules"
    },

    # -------------------------------------------------------------------
    # 3. SQL INJECTION DETECTION
    # -------------------------------------------------------------------
    # WHAT IS SQL INJECTION?
    #   Attacker inserts malicious SQL code into web forms to steal
    #   or manipulate database data.
    #   Example: typing " OR 1=1; DROP TABLE users; -- " in a login form.
    #
    # HOW WE DETECT IT:
    #   Look for SQL keywords in HTTP request payloads.
    # -------------------------------------------------------------------
    "SQL_INJECTION": {
        "name": "SQL Injection Attempt",
        "description": "Malicious SQL code injected into web requests",
        "severity": "CRITICAL",
        "patterns": [
            "SELECT * FROM",
            "DROP TABLE",
            "INSERT INTO",
            "UNION SELECT",
            "OR 1=1",
            "'; --",
            "exec(",
            "xp_cmdshell",
            "information_schema",
            "WAITFOR DELAY"
        ],
        "color": "#8e44ad",
        "icon": "💉",
        "how_to_prevent": "Use parameterized queries, input validation, WAF"
    },

    # -------------------------------------------------------------------
    # 4. BRUTE FORCE LOGIN DETECTION
    # -------------------------------------------------------------------
    # WHAT IS BRUTE FORCE?
    #   Attacker tries THOUSANDS of username/password combinations
    #   automatically until one works (like trying every key on a keyring).
    #
    # HOW WE DETECT IT:
    #   Too many failed login attempts from same IP in short time.
    # -------------------------------------------------------------------
    "BRUTE_FORCE": {
        "name": "Brute Force Login Attack",
        "description": "Repeated login attempts indicating password guessing",
        "severity": "HIGH",
        "threshold_attempts": 5,      # If > 5 failed logins in 30 seconds → Alert!
        "time_window": 30,
        "target_ports": [22, 21, 3306, 3389, 23],  # SSH, FTP, MySQL, RDP, Telnet
        "color": "#e67e22",
        "icon": "🔨",
        "how_to_prevent": "Multi-factor auth, account lockout, CAPTCHA"
    },

    # -------------------------------------------------------------------
    # 5. PING OF DEATH / ICMP FLOOD
    # -------------------------------------------------------------------
    # WHAT IS ICMP FLOOD?
    #   Attacker sends massive ping (ICMP) packets to crash/slow a target.
    #   Traditional "Ping of Death" used oversized packets.
    #
    # HOW WE DETECT IT:
    #   Excessive ICMP packets from one source.
    # -------------------------------------------------------------------
    "ICMP_FLOOD": {
        "name": "ICMP Flood / Ping of Death",
        "description": "Excessive ping packets flooding the network",
        "severity": "MEDIUM",
        "threshold_packets": 50,      # If > 50 ICMP packets in 1 second → Alert!
        "time_window": 1,
        "color": "#f39c12",
        "icon": "📡",
        "how_to_prevent": "Block ICMP at firewall, rate limit ping responses"
    },

    # -------------------------------------------------------------------
    # 6. XSS (CROSS SITE SCRIPTING) DETECTION
    # -------------------------------------------------------------------
    # WHAT IS XSS?
    #   Attacker injects malicious JavaScript into web pages.
    #   When victims visit the page, their browser runs attacker's code.
    #   Can steal cookies, session tokens, redirect users.
    #
    # HOW WE DETECT IT:
    #   Look for HTML/JS injection patterns in HTTP requests.
    # -------------------------------------------------------------------
    "XSS": {
        "name": "Cross-Site Scripting (XSS)",
        "description": "Malicious scripts injected into web content",
        "severity": "HIGH",
        "patterns": [
            "<script>",
            "javascript:",
            "onerror=",
            "onload=",
            "alert(",
            "document.cookie",
            "eval(",
            "<iframe",
            "onmouseover="
        ],
        "color": "#16a085",
        "icon": "⚡",
        "how_to_prevent": "Input sanitization, Content Security Policy (CSP), output encoding"
    },

    # -------------------------------------------------------------------
    # 7. DNS AMPLIFICATION (DDoS)
    # -------------------------------------------------------------------
    # WHAT IS DNS AMPLIFICATION?
    #   Attacker sends small DNS queries with spoofed victim IP.
    #   DNS servers respond with LARGE replies to victim → victim overwhelmed.
    #   Small request → Big response = Amplification!
    #
    # HOW WE DETECT IT:
    #   Unusually large DNS responses or too many DNS queries.
    # -------------------------------------------------------------------
    "DNS_AMPLIFICATION": {
        "name": "DNS Amplification Attack",
        "description": "Exploiting DNS to amplify traffic toward a target",
        "severity": "HIGH",
        "threshold_packets": 30,
        "target_port": 53,            # DNS runs on port 53
        "time_window": 1,
        "color": "#2980b9",
        "icon": "🌐",
        "how_to_prevent": "Disable open DNS resolvers, BCP38 filtering, rate limiting"
    },
}

# =======================================================================
# WELL-KNOWN DANGEROUS PORTS
# =======================================================================
# These ports are commonly used by attackers or malware.
# Normal users shouldn't be accessing these unexpectedly.
# =======================================================================
SUSPICIOUS_PORTS = {
    1337: "Commonly used by hackers/backdoors",
    4444: "Metasploit default reverse shell port",
    6666: "IRC used by botnets",
    6667: "IRC botnet communication",
    31337: "Élite hacker port (Back Orifice trojan)",
    12345: "NetBus trojan",
    27374: "Sub7 trojan",
    65535: "Max port - often scanned",
    5555: "Android Debug Bridge (ADB) exploitation",
    9001: "Tor network relay port"
}

# =======================================================================
# PRIVATE/RESERVED IP RANGES (RFC 1918)
# =======================================================================
# These IPs are used internally. If we see external traffic claiming
# to come from these IPs, it's IP SPOOFING!
# =======================================================================
PRIVATE_IP_RANGES = [
    "10.",          # 10.0.0.0/8
    "172.16.",      # 172.16.0.0/12
    "172.17.",
    "172.18.",
    "192.168.",     # 192.168.0.0/16
    "127.",         # Loopback
]

# =======================================================================
# SEVERITY LEVEL DEFINITIONS
# =======================================================================
SEVERITY_LEVELS = {
    "LOW":      {"color": "#27ae60", "priority": 1, "action": "Log and monitor"},
    "MEDIUM":   {"color": "#f39c12", "priority": 2, "action": "Alert administrator"},
    "HIGH":     {"color": "#e74c3c", "priority": 3, "action": "Block and alert immediately"},
    "CRITICAL": {"color": "#c0392b", "priority": 4, "action": "Emergency response required"},
}
