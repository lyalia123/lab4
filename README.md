Raft Lite — Lab 3
Overview

This project implements a simplified Raft protocol (Raft Lite) for educational purposes. It demonstrates:

Leader election with randomized timeouts

Heartbeats to maintain leader authority

Log replication with majority-based commit

Crash-stop recovery for both leader and follower nodes

Cluster is deployed on AWS EC2 instances with private IPs.

Cluster Setup

This example uses 3 nodes: A, B, C. Each node runs as an independent process.

Node A
python3 node.py --id A --port 8000 --peers B=172.31.73.173:8001,C=172.31.71.208:8002

Node B
python3 node.py --id B --port 8001 --peers A=172.31.68.113:8000,C=172.31.71.208:8002

Node C
python3 node.py --id C --port 8002 --peers A=172.31.68.113:8000,B=172.31.73.173:8001


Notes:

Nodes must be started in separate terminals.

Nodes start as Followers. Leader election occurs automatically if no heartbeat is received.

Client Interaction

Use client.py to send commands to the current leader.

python3 client.py --leader <LEADER_IP>:<LEADER_PORT> --cmd "SET x=5"


Example:

python3 client.py --leader 172.31.68.113:8000 --cmd "SET x=5"


Command is appended to the leader's log.

It is replicated to followers.

Entry is committed after majority acknowledgment.

Failure Experiments
Scenario A — Leader Crash

Stop the current leader (Ctrl+C).

Observe a new leader election.

Send new commands via the client.

Restart the crashed leader — it will catch up with all committed entries.

Scenario B — Follower Crash

Stop a follower node.

Send commands to the leader.

Restart the crashed follower — it will automatically catch up with missing log entries.

Logs / Expected Output

Leader logs:

[Leader A] Append log entry (term=1, index=0, cmd=SET x=5)
[Leader A] Entry committed (index=0) cmd='SET x=5'


Follower logs:

[Node B] Append success (+1 entries), logLen=1
[Node C] Append success (+1 entries), logLen=1
[Node B] Committed index=0 cmd='SET x=5'
[Node C] Committed index=0 cmd='SET x=5'


Heartbeat logs:

[Leader A] Sending heartbeat
[Node B] Received heartbeat from Leader A (term 1)
[Node C] Received heartbeat from Leader A (term 1)

Requirements

Python 3.10+

asyncio (built-in)

JSON (built-in)

Network connectivity between EC2 private IPs (Security Group allows port 8000–8002)
