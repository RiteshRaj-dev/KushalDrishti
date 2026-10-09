"""One simulated edge node per centre in data/centres.json, so the national map comes alive."""
import json, os, random, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_node import EdgeNode

host, port = os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "1883"))
interval = float(os.environ.get("FLEET_INTERVAL", "3"))
centres = json.load(open(os.environ.get("CENTRES_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "centres.json"))))
random.seed(7)
nodes = []
for ct in centres:
    sc = random.choices(["ok", "ghost", "equipment"], [0.7, 0.2, 0.1])[0]
    nodes.append(EdgeNode(ct["code"], host, port, f"data/{ct['code']}.db", sc)); print(ct["code"], sc)
def loop(node, offset):
    time.sleep(offset)
    while True:
        node.tick(); time.sleep(interval)
for i, n in enumerate(nodes):
    threading.Thread(target=loop, args=(n, i * 0.3), daemon=True).start()
while True:
    time.sleep(60)
