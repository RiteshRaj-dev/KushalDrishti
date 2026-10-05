import time
import threading
from edge_node import ITIEdgeNode

# Simulated National Registry of ITI Centres
# Format: (Centre Code, Claimed Attendance on Portal, Is Cheating?)
FLEET_CONFIG = [
    ("ITI-DL-001", 30, False),  # Honest centre
    ("ITI-DL-002", 25, False),  # Honest centre
    ("ITI-MH-042", 40, True),   # Cheating centre (Ghost Attendance)
    ("ITI-UP-105", 28, False),  # Honest centre
    ("ITI-KA-088", 35, True),   # Cheating centre (Ghost Attendance)
]

def simulate_node(config):
    node = ITIEdgeNode(centre_code=config[0], claimed_attendance=config[1], is_cheating=config[2])
    node.connect()
    
    # Send a packet every 10 seconds for the demo (in production, this is every 1 minute)
    while True:
        node.run_inference_cycle()
        time.sleep(10)

if __name__ == "__main__":
    print("===================================================")
    print("KUSHALDRISHTI EDGE FLEET SIMULATOR INITIATED")
    print("===================================================")
    time.sleep(5)  # Wait for Mosquitto and API to boot
    
    threads = []
    for config in FLEET_CONFIG:
        t = threading.Thread(target=simulate_node, args=(config,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(1) # Stagger startups
        
    # Keep main thread alive
    while True:
        time.sleep(1)