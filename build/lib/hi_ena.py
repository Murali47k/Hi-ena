import argparse
import sys

from server.main import start_server
from client.main import main as client_main

def main():
    parser = argparse.ArgumentParser(prog="Hi-ena", description="LAN Chat + File Sharing")
    sub = parser.add_subparsers(dest="command", required=True)

    # Start server
    serverp = sub.add_parser("server", help="Start a server")
    serverp.add_argument("--host", default="0.0.0.0")
    serverp.add_argument("--port", type=int, default=5555)

    # Client (reuse your client.main logic)
    clientp = sub.add_parser("client", help="Run client commands (host-server/join-server)")
    clientp.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "server":
        start_server(host=args.host, port=args.port)

    elif args.command == "client":
        sys.argv = ["client.main"] + args.args
        client_main()

if __name__ == "__main__":
    main()
