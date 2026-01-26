Distributed Transactions Lab (2PC / 3PC)

This project implements distributed transactions using Two-Phase Commit (2PC) and Three-Phase Commit (3PC) protocols across multiple EC2 nodes. The system demonstrates atomicity, consistency, and fault tolerance in a simple key-value store.

🟢 Components

Coordinator — initiates transactions, collects votes, and decides commit/abort.

Participant (Resource Manager) — votes on transactions, applies operations locally, maintains WAL.

Client — triggers transactions on the coordinator.

⚙️ Requirements

Python 3.x

Standard library only (HTTP server and client)

EC2 instances or local machines for multiple nodes

💻 Usage
1. Start Participants
# Node B
python3 participant.py --id B --port 8001 --wal /tmp/B.wal

# Node C
python3 participant.py --id C --port 8002 --wal /tmp/C.wal

2. Start Coordinator
python3 coordinator.py --id COORD --port 8000 --participants http://<B-IP>:8001,http://<C-IP>:8002

3. Start Client & Trigger Transactions
# 2PC transaction
python3 client.py --coord http://<COORD-IP>:8000 start TX1 2PC SET x 5

# 3PC transaction
python3 client.py --coord http://<COORD-IP>:8000 start TX2 3PC SET y 10

4. Check Status
# Coordinator status
curl http://<COORD-IP>:8000/status

# Participant status
curl http://<PARTICIPANT-IP>:<PORT>/status
