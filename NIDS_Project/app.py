"""
=======================================================================
  FILE: app.py  (Flask Web Server)
  PROJECT: Network Intrusion Detection System (NIDS)
  STUDENT: Harsh Soam, Abhishek Arya
  TEACHER: Mr. Varun Chaudhary
=======================================================================

  WHAT IS THIS FILE?
  ------------------
  This is the WEB SERVER that powers our NIDS dashboard.
  It uses FLASK — a lightweight Python web framework.

  HOW IT WORKS (Client-Server Architecture):
  -------------------------------------------
  Browser (Client)  ←→  Flask (Server)  ←→  Detector Engine
       ↑                      ↑
  index.html              app.py (this file)
  dashboard.js         
  style.css
  
  The browser connects to http://localhost:5000
  Flask serves the HTML page AND provides API endpoints.
  
  WHAT IS AN API ENDPOINT?
  -------------------------
  An endpoint is a URL that returns DATA (not HTML).
  Our dashboard JavaScript calls these every few seconds
  to get the latest alerts and stats — this is called
  "AJAX polling" (Asynchronous JavaScript).
  
  OUR API ENDPOINTS:
  ------------------
  GET /              → Serve the HTML dashboard
  GET /api/stats     → Return current network stats (JSON)
  GET /api/alerts    → Return latest alerts (JSON)
  POST /api/reset    → Reset all stats
=======================================================================
"""

from flask import Flask, jsonify, render_template, request
import threading
import time
import json

from traffic_simulator import TrafficSimulator
from detector import IntrusionDetector

# =======================================================================
# INITIALIZE FLASK APP
# =======================================================================
# '__name__' tells Flask where to find templates and static files.
# Flask will look in ./templates/ for HTML and ./static/ for CSS/JS.
# =======================================================================
app = Flask(__name__)

# =======================================================================
# CREATE CORE COMPONENTS
# =======================================================================
simulator = TrafficSimulator()    # Generates fake traffic
detector = IntrusionDetector()    # Analyzes packets for attacks

# Global flag to control the processing loop
nids_running = False


# =======================================================================
# BACKGROUND NIDS PROCESSING LOOP
# =======================================================================
def run_nids():
    """
    Main NIDS processing loop running in a background thread.
    
    HOW IT WORKS:
    1. Get batch of packets from simulator
    2. Feed each packet to the detector
    3. Detector generates alerts (stored internally)
    4. Dashboard reads alerts via API
    5. Repeat every 0.1 seconds
    
    WHY A SEPARATE THREAD?
    Flask runs in the main thread serving HTTP requests.
    If NIDS processing ran there too, the web server would be blocked!
    Background thread = parallel processing.
    
    THREAD SAFETY:
    The detector and simulator use locks internally for thread safety.
    This function just orchestrates them.
    """
    global nids_running
    print("[NIDS] Background processing started...")
    
    while nids_running:
        # Get latest batch of packets
        packets = simulator.get_packets(max_packets=30)
        
        # Analyze each packet
        for packet in packets:
            detector.analyze_packet(packet)
        
        # Small sleep to prevent CPU from running at 100%
        # 0.1 seconds = 10 iterations per second
        time.sleep(0.1)
    
    print("[NIDS] Background processing stopped.")


def seed_initial_data():
    """
    Seed baseline traffic and representative alerts so the dashboard starts
    immediately populated with rich, realistic data right on launch.
    """
    print("[NIDS] Seeding initial baseline network data...")
    # Seed normal packets
    for _ in range(25):
        for pkt in simulator._normal_http_traffic() + simulator._normal_dns_traffic():
            detector.analyze_packet(pkt)
    
    # Seed initial attack samples across all categories
    attacks = [
        simulator._port_scan_attack,
        simulator._sql_injection_attack,
        simulator._brute_force_attack,
        simulator._syn_flood_attack,
        simulator._icmp_flood_attack,
        simulator._xss_attack,
    ]
    for attack_func in attacks:
        for pkt in attack_func():
            detector.analyze_packet(pkt)
    print(f"[NIDS] Initial seed complete: {detector.stats['total_packets']} packets, {detector.stats['total_alerts']} alerts ready.")


# =======================================================================
# START NIDS ON APP LAUNCH
# =======================================================================
def start_nids():
    """Start the NIDS system (simulator + detector + processing thread)."""
    global nids_running
    nids_running = True
    
    # Pre-seed initial data so the dashboard is immediately populated
    seed_initial_data()
    
    # Start traffic simulator
    simulator.start()
    
    # Start background NIDS processing thread
    # daemon=True → thread dies automatically when main program exits
    nids_thread = threading.Thread(target=run_nids, daemon=True)
    nids_thread.start()
    
    print("[NIDS] System fully started!")


# =======================================================================
# FLASK ROUTES (API ENDPOINTS)
# =======================================================================

@app.route("/")
def index():
    """
    Serve the main dashboard HTML page.
    
    render_template() reads index.html from the /templates/ folder
    and sends it to the browser.
    """
    return render_template("index.html")


@app.route("/api/stats")
def get_stats():
    """
    API endpoint: Returns current network statistics as JSON.
    
    The dashboard JavaScript calls this every 2 seconds.
    
    RESPONSE FORMAT:
    {
        "total_packets": 1250,
        "total_alerts": 23,
        "packets_per_second": 45,
        "attack_counts": {"PORT_SCAN": 5, "SQL_INJECTION": 3, ...},
        "severity_counts": {"LOW": 2, "MEDIUM": 5, "HIGH": 10, "CRITICAL": 6},
        ...
    }
    
    jsonify() converts Python dict to proper JSON response with
    correct Content-Type header (application/json).
    """
    stats = detector.get_stats()
    stats["simulator_total"] = simulator.total_generated
    return jsonify(stats)


@app.route("/api/alerts")
def get_alerts():
    """
    API endpoint: Returns the 20 most recent alerts.
    
    The dashboard calls this every 2 seconds and updates the alert table.
    """
    count = request.args.get("count", 20, type=int)
    alerts = detector.get_recent_alerts(count)
    return jsonify({"alerts": alerts, "count": len(alerts)})


@app.route("/api/reset", methods=["POST"])
def reset_stats():
    """
    API endpoint: Reset all detector stats.
    Called when user clicks "Reset" button in dashboard.
    
    POST method is used because it MODIFIES server state
    (GET is for reading, POST/PUT for modifying).
    """
    detector.stats["total_packets"] = 0
    detector.stats["total_alerts"] = 0
    detector.stats["attack_counts"].clear()
    detector.stats["severity_counts"] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    detector.stats["blocked_ips"].clear()
    detector.alerts.clear()
    return jsonify({"status": "reset", "message": "All stats cleared"})


@app.route("/api/simulate/<attack_type>", methods=["POST"])
def trigger_attack(attack_type):
    """
    API endpoint: Manually trigger a specific attack simulation.
    Called when user clicks attack type buttons in dashboard.
    
    Path parameter: <attack_type> is extracted from URL.
    Example: POST /api/simulate/PORT_SCAN triggers a port scan.
    """
    valid_attacks = ["port_scan", "syn_flood", "sql_injection", 
                    "brute_force", "icmp_flood", "xss"]
    
    if attack_type.lower() not in valid_attacks:
        return jsonify({"error": f"Unknown attack type: {attack_type}"}), 400
    
    # Map to simulator method
    attack_method_map = {
        "port_scan":     simulator._port_scan_attack,
        "syn_flood":     simulator._syn_flood_attack,
        "sql_injection": simulator._sql_injection_attack,
        "brute_force":   simulator._brute_force_attack,
        "icmp_flood":    simulator._icmp_flood_attack,
        "xss":           simulator._xss_attack,
    }
    
    # Generate and immediately process attack packets
    attack_packets = attack_method_map[attack_type.lower()]()
    for packet in attack_packets:
        detector.analyze_packet(packet)
    
    return jsonify({
        "status": "triggered",
        "attack": attack_type,
        "packets_generated": len(attack_packets),
        "message": f"Simulated {attack_type} attack with {len(attack_packets)} packets"
    })


# =======================================================================
# ENTRY POINT
# =======================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  NETWORK INTRUSION DETECTION SYSTEM (NIDS)")
    print("  Students: Harsh Soam, Abhishek Arya")
    print("  Teacher:  Mr. Varun Chaudhary")
    print("=" * 60)
    
    # Start the NIDS engine
    start_nids()
    
    print("\n[INFO] Dashboard available at: http://localhost:5000")
    print("[INFO] Press Ctrl+C to stop\n")
    
    # Start Flask development server
    # debug=False in production! debug=True auto-reloads on code changes
    # use_reloader=False prevents Flask from starting NIDS twice in debug mode
    app.run(
        host="0.0.0.0",    # Listen on all network interfaces
        port=5000,
        debug=False,        # Set True during development only
        use_reloader=False, # Prevent double-start issue
        threaded=True       # Handle multiple browser requests simultaneously
    )
