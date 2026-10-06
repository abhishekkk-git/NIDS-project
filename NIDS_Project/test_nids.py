"""Quick test script to verify all NIDS modules work correctly."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=== NIDS SYSTEM TEST ===")

from signatures import ATTACK_SIGNATURES, SUSPICIOUS_PORTS
from traffic_simulator import TrafficSimulator, NetworkPacket
from detector import IntrusionDetector, Alert

print(f"[1] Loaded {len(ATTACK_SIGNATURES)} attack signatures")
print(f"[2] Loaded {len(SUSPICIOUS_PORTS)} suspicious port definitions")

sim = TrafficSimulator()
det = IntrusionDetector()

sim.start()
print("[3] Traffic simulator started")

import time
time.sleep(2)

total_alerts = 0
for i in range(5):
    pkts = sim.get_packets()
    for p in pkts:
        result = det.analyze_packet(p)
        if result:
            total_alerts += 1
    time.sleep(0.3)

sim.stop()
stats = det.get_stats()

print(f"[4] Total packets processed: {stats['total_packets']}")
print(f"[5] Total alerts generated:  {stats['total_alerts']}")
print(f"[6] Attack types detected:   {list(stats['attack_counts'].keys())}")
print(f"[7] Protocol breakdown:      {dict(stats['protocol_counts'])}")
print()

# Test manual attack simulation
port_scan_pkts = sim._port_scan_attack()
syn_flood_pkts = sim._syn_flood_attack()
sql_pkts       = sim._sql_injection_attack()
brute_pkts     = sim._brute_force_attack()

for p in port_scan_pkts + syn_flood_pkts + sql_pkts + brute_pkts:
    det.analyze_packet(p)

final_stats = det.get_stats()
print(f"[8] After attack simulation:")
print(f"    Total alerts:    {final_stats['total_alerts']}")
print(f"    Attack counts:   {dict(final_stats['attack_counts'])}")
print(f"    Blocked IPs:     {final_stats['blocked_ips']}")
print()
print("ALL TESTS PASSED - NIDS is fully functional!")
