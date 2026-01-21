#!/usr/bin/env python3
import argparse, json, asyncio

async def send(host, port, msg, timeout=2.0):
    reader, writer = await asyncio.open_connection(host, port)
    writer.write((json.dumps(msg) + "\n").encode())
    await writer.drain()
    line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return json.loads(line.decode()) if line else None

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leader", required=True, help="ip:port")
    ap.add_argument("--cmd", required=True, help='e.g. "SET x=5"')
    args = ap.parse_args()

    host, port = args.leader.split(":")
    port = int(port)

    resp = await send(host, port, {"type": "ClientCommand", "cmd": args.cmd})
    print("Response:", resp)

if __name__ == "__main__":
    asyncio.run(main())
