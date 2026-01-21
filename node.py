#!/usr/bin/env python3
import asyncio, json, random, time, argparse
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------
# Raft Lite (educational, simplified)
# - Leader election (RequestVote) with randomized timeouts
# - Heartbeats + log replication (AppendEntries)
# - Majority commit
# - Crash-stop failures: stop a node with Ctrl+C
# Notes:
# - This is intentionally simplified (no log conflict resolution,
#   no log up-to-date check on votes, no snapshots).
# - Good enough for a lab demo: election, replication, failover.
# ------------------------------------------------------------

def now_ms() -> int:
    return int(time.time() * 1000)

def jdump(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))

async def send_json(host: str, port: int, msg: dict, timeout: float = 1.2) -> Optional[dict]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.write((jdump(msg) + "\n").encode())
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        if not line:
            return None
        return json.loads(line.decode())
    except Exception:
        return None

class RaftNode:
    def __init__(self, node_id: str, host: str, port: int, peers: Dict[str, Tuple[str, int]]):
        self.id = node_id
        self.host = host
        self.port = port
        self.peers = peers  # peerId -> (host,port)

        # Core Raft state
        self.currentTerm = 0
        self.votedFor: Optional[str] = None
        self.log: List[dict] = []  # [{term:int, cmd:str}]
        self.commitIndex = -1
        self.state = "Follower"  # Follower | Candidate | Leader

        # Runtime
        self.leaderId: Optional[str] = None
        self.lastHeartbeatMs = now_ms()
        self.election_deadline_ms = self._new_election_deadline()

        # Leader replication tracking
        self.nextIndex: Dict[str, int] = {pid: 0 for pid in self.peers}
        self.matchIndex: Dict[str, int] = {pid: -1 for pid in self.peers}

        self.heartbeat_interval = 0.8  # seconds
        self.running = True
        self.lock = asyncio.Lock()

    def _new_election_deadline(self) -> int:
        return now_ms() + random.randint(2500, 4500)

    def _majority(self) -> int:
        n = 1 + len(self.peers)
        return (n // 2) + 1

    def _print(self, msg: str):
        print(f"[Node {self.id}] {msg}", flush=True)

    def _print_leader(self, msg: str):
        print(f"[Leader {self.id}] {msg}", flush=True)

    async def handle_message(self, msg: dict) -> dict:
        t = msg.get("type")
        if t == "RequestVote":
            return await self.on_request_vote(msg)
        if t == "AppendEntries":
            return await self.on_append_entries(msg)
        if t == "ClientCommand":
            return await self.on_client_command(msg)
        return {"type": "Error", "error": "unknown_type"}

    async def on_request_vote(self, msg: dict) -> dict:
        async with self.lock:
            term = int(msg.get("term", 0))
            candidateId = msg.get("candidateId")

            if term > self.currentTerm:
                self.currentTerm = term
                self.state = "Follower"
                self.votedFor = None
                self.leaderId = None

            voteGranted = False
            if term == self.currentTerm and (self.votedFor is None or self.votedFor == candidateId):
                # Lite: no log up-to-date check
                self.votedFor = candidateId
                voteGranted = True
                self.lastHeartbeatMs = now_ms()
                self.election_deadline_ms = self._new_election_deadline()
                self._print(f"Voted for {candidateId} (term {self.currentTerm})")

            return {"type": "VoteResponse", "term": self.currentTerm, "voteGranted": voteGranted}

    async def on_append_entries(self, msg: dict) -> dict:
        async with self.lock:
            term = int(msg.get("term", 0))
            leaderId = msg.get("leaderId")
            entries = msg.get("entries", [])
            leaderCommit = int(msg.get("leaderCommit", -1))

            if term < self.currentTerm:
                return {"type": "AppendResponse", "term": self.currentTerm, "success": False, "matchIndex": len(self.log) - 1}

            # Accept leader / step down
            if term > self.currentTerm:
                self.currentTerm = term
                self.votedFor = None
            self.state = "Follower"
            self.leaderId = leaderId
            self.lastHeartbeatMs = now_ms()
            self.election_deadline_ms = self._new_election_deadline()

            # Lite replication: append whatever leader sends (no conflict resolution)
            if entries:
                for e in entries:
                    self.log.append({"term": int(e["term"]), "cmd": str(e["cmd"])})
                self._print(f"Append success (+{len(entries)} entries), logLen={len(self.log)}")

            # Commit up to leaderCommit
            if leaderCommit > self.commitIndex:
                newCommit = min(leaderCommit, len(self.log) - 1)
                if newCommit > self.commitIndex:
                    for i in range(self.commitIndex + 1, newCommit + 1):
                        self._print(f"Committed index={i} cmd='{self.log[i]['cmd']}'")
                    self.commitIndex = newCommit

            return {"type": "AppendResponse", "term": self.currentTerm, "success": True, "matchIndex": len(self.log) - 1}

    async def on_client_command(self, msg: dict) -> dict:
        async with self.lock:
            cmd = str(msg.get("cmd", "")).strip()
            if not cmd:
                return {"type": "ClientResponse", "ok": False, "error": "empty_cmd"}

            if self.state != "Leader":
                # if we know leader, hint it
                return {"type": "ClientResponse", "ok": False, "redirect": self.leaderId}

            entry = {"term": self.currentTerm, "cmd": cmd}
            self.log.append(entry)
            index = len(self.log) - 1
            self._print_leader(f"Append log entry (term={self.currentTerm}, index={index}, cmd={cmd})")

        # replicate outside lock
        await self.replicate_to_all()
        await self.advance_commit()

        async with self.lock:
            return {"type": "ClientResponse", "ok": True, "leader": self.id, "index": index, "commitIndex": self.commitIndex}

    async def start_election(self):
        async with self.lock:
            self.state = "Candidate"
            self.currentTerm += 1
            term = self.currentTerm
            self.votedFor = self.id
            self.leaderId = None
            self.election_deadline_ms = self._new_election_deadline()
            self._print(f"Timeout -> Candidate (term {term})")

        votes = 1
        needed = self._majority()

        async def ask(pid: str, host: str, port: int):
            nonlocal votes
            resp = await send_json(host, port, {"type": "RequestVote", "term": term, "candidateId": self.id})
            if not resp:
                return
            async with self.lock:
                rterm = int(resp.get("term", 0))
                if rterm > self.currentTerm:
                    self.currentTerm = rterm
                    self.state = "Follower"
                    self.votedFor = None
                    return
                if self.state != "Candidate" or self.currentTerm != term:
                    return
                if resp.get("voteGranted"):
                    votes += 1

        tasks = [asyncio.create_task(ask(pid, hp[0], hp[1])) for pid, hp in self.peers.items()]
        if tasks:
            await asyncio.gather(*tasks)

        async with self.lock:
            if self.state == "Candidate" and self.currentTerm == term and votes >= needed:
                self.state = "Leader"
                self.leaderId = self.id
                for pid in self.peers:
                    self.nextIndex[pid] = 0
                    self.matchIndex[pid] = -1
                self._print(f"Received votes -> Leader (term {term}, votes={votes}/{1+len(self.peers)})")

    async def replicate_to_peer(self, pid: str, host: str, port: int):
        async with self.lock:
            if self.state != "Leader":
                return
            term = self.currentTerm
            next_i = self.nextIndex[pid]
            entries = self.log[next_i:]
            payload = {
                "type": "AppendEntries",
                "term": term,
                "leaderId": self.id,
                "entries": entries,
                "leaderCommit": self.commitIndex,
            }

        resp = await send_json(host, port, payload, timeout=1.2)
        if not resp:
            return

        async with self.lock:
            rterm = int(resp.get("term", 0))
            if rterm > self.currentTerm:
                self.currentTerm = rterm
                self.state = "Follower"
                self.votedFor = None
                self.leaderId = None
                return
            if self.state != "Leader":
                return
            if resp.get("success"):
                mi = int(resp.get("matchIndex", -1))
                self.matchIndex[pid] = mi
                self.nextIndex[pid] = mi + 1

    async def replicate_to_all(self):
        async with self.lock:
            if self.state != "Leader":
                return
            peer_items = list(self.peers.items())
        tasks = [asyncio.create_task(self.replicate_to_peer(pid, hp[0], hp[1])) for pid, hp in peer_items]
        if tasks:
            await asyncio.gather(*tasks)

    async def advance_commit(self):
        async with self.lock:
            if self.state != "Leader":
                return
            maj = self._majority()
            last_index = len(self.log) - 1
            new_commit = self.commitIndex
            for i in range(self.commitIndex + 1, last_index + 1):
                count = 1
                for pid in self.peers:
                    if self.matchIndex.get(pid, -1) >= i:
                        count += 1
                if count >= maj:
                    new_commit = i
            if new_commit > self.commitIndex:
                for i in range(self.commitIndex + 1, new_commit + 1):
                    self._print_leader(f"Entry committed (index={i}) cmd='{self.log[i]['cmd']}'")
                self.commitIndex = new_commit

    async def ticker(self):
        while self.running:
            await asyncio.sleep(0.15)
            async with self.lock:
                st = self.state
                deadline = self.election_deadline_ms

            if st != "Leader" and now_ms() >= deadline:
                await self.start_election()

            async with self.lock:
                st = self.state
            if st == "Leader":
                await self.replicate_to_all()
                await self.advance_commit()
                await asyncio.sleep(self.heartbeat_interval)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, node: RaftNode):
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not line:
            writer.close()
            return
        msg = json.loads(line.decode())
        resp = await node.handle_message(msg)
        writer.write((jdump(resp) + "\n").encode())
        await writer.drain()
    except Exception:
        try:
            writer.write((jdump({"type": "Error", "error": "bad_request"}) + "\n").encode())
            await writer.drain()
        except Exception:
            pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peers", required=True, help="Format: B=ip:port,C=ip:port")
    args = ap.parse_args()

    peers: Dict[str, Tuple[str, int]] = {}
    peers_str = args.peers.strip()
    if peers_str:
        for part in peers_str.split(","):
            part = part.strip()
            if not part:
                continue
            pid, addr = part.split("=")
            host, p = addr.split(":")
            peers[pid.strip()] = (host.strip(), int(p.strip()))

    node = RaftNode(args.id, args.host, args.port, peers)
    node._print(f"Starting on {args.host}:{args.port} peers={peers}")

    server = await asyncio.start_server(lambda r, w: handle_client(r, w, node), host=args.host, port=args.port)
    asyncio.create_task(node.ticker())

    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    node._print(f"Listening on {addrs}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
