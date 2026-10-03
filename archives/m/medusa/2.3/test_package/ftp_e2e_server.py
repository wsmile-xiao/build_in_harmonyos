#!/usr/bin/env python3
"""A deterministic, minimal FTP server for the medusa consumer test (L0d).

Why this exists
---------------
`medusa -d' only proves that the binary starts and can dlopen its modules; it
never drives a real audit.  This server gives the consumer test a live target
holding exactly one valid credential pair, so `medusa -M ftp' really performs an
end-to-end audit: the packaged binary connects, runs the FTP USER/PASS dialogue,
recognises the valid credential and reports it.

Only the Python standard library is used on purpose - the OHOS test image has
python3 but no third-party FTP package, and a real server (vsftpd/proftpd) is
not available either.

Protocol subset (exactly what src/modsrc/ftp.c in medusa 2.3 needs):
  220 <banner>   on connect
  USER -> 331    (the module requires a 331 after USER)
  PASS -> 230    when the credential matches, 530 otherwise
  QUIT -> 221    (then the connection is closed)
Anything else gets 502, so a wrong credential can never look valid.

Every client command is echoed to stderr as `E2E <COMMAND>`, which lets the
caller prove the dialogue happened on the wire instead of trusting the exit
status alone.

Usage: ftp_e2e_server.py [--port N] [--user U] [--pass P]
         [--user2 U] [--pass2 P] [--rounds N]
"""
import argparse
import os
import socket
import sys

BANNER = b"220 medusa-e2e-ftpd ready\r\n"
REPLY_NEED_PASS = b"331 Please specify the password.\r\n"
REPLY_LOGIN_OK = b"230 Login successful.\r\n"
REPLY_LOGIN_BAD = b"530 Login incorrect.\r\n"
REPLY_GOODBYE = b"221 Goodbye.\r\n"
REPLY_SYST = b"215 UNIX Type: L8\r\n"
REPLY_FEAT = b"211 End\r\n"
REPLY_UNKNOWN = b"502 Command not implemented.\r\n"


def log(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def credentials(args):
    """Return the list of accepted (user, password) pairs."""
    pairs = [(args.user, args.password)]
    if args.user2 or args.password2:
        pairs.append((args.user2, args.password2))
    return [p for p in pairs if p[0]]


def serve_one(conn, args, pairs):
    """Run the USER/PASS dialogue for one connection; True if it authenticated."""
    authenticated = False
    current_user = ""
    with conn:
        conn.settimeout(args.timeout)
        conn.sendall(BANNER)
        buf = b""
        while True:
            try:
                chunk = conn.recv(4096)
            except (socket.timeout, ConnectionResetError, OSError):
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                raw, _, buf = buf.partition(b"\n")
                line = raw.decode("ascii", "replace").strip("\r")
                if not line:
                    continue
                verb, _, arg = line.partition(" ")
                log("E2E " + line)
                cmd = verb.upper()
                if cmd == "USER":
                    current_user = arg
                    conn.sendall(REPLY_NEED_PASS)
                elif cmd == "PASS":
                    if (current_user, arg) in pairs:
                        authenticated = True
                        conn.sendall(REPLY_LOGIN_OK)
                    else:
                        conn.sendall(REPLY_LOGIN_BAD)
                elif cmd == "QUIT":
                    conn.sendall(REPLY_GOODBYE)
                    return authenticated
                elif cmd == "SYST":
                    conn.sendall(REPLY_SYST)
                elif cmd == "FEAT":
                    conn.sendall(REPLY_FEAT)
                else:
                    conn.sendall(REPLY_UNKNOWN)
    return authenticated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0,
                    help="TCP port; 0 lets the OS pick a free one")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--user", default=os.environ.get("MEDUSA_E2E_USER", "e2euser"))
    ap.add_argument("--pass", dest="password",
                    default=os.environ.get("MEDUSA_E2E_PASS", "e2epass"))
    ap.add_argument("--user2", default=os.environ.get("MEDUSA_E2E_USER2", ""))
    ap.add_argument("--pass2", dest="password2",
                    default=os.environ.get("MEDUSA_E2E_PASS2", ""))
    ap.add_argument("--rounds", type=int, default=1,
                    help="connections to serve before exiting (0 = unlimited)")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    pairs = credentials(args)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(8)
    port = srv.getsockname()[1]
    log(f"FTPD_READY host={args.host} port={port}")
    log("FTPD_CREDENTIALS user=%s password=%s" % (pairs[0][0], pairs[0][1]))

    served = 0
    successes = 0
    srv.settimeout(args.timeout * 4)
    try:
        while args.rounds == 0 or served < args.rounds:
            try:
                conn, peer = srv.accept()
            except (socket.timeout, OSError):
                break
            served += 1
            log(f"E2E CONNECT from={peer[0]}:{peer[1]} n={served}")
            try:
                if serve_one(conn, args, pairs):
                    successes += 1
                    log(f"E2E AUTH_OK n={served}")
            except Exception as exc:  # noqa: BLE001 - test server: never crash
                log(f"E2E ERROR {type(exc).__name__}: {exc}")
                break
    finally:
        srv.close()
    log(f"FTPD_DONE served={served} auth_ok={successes}")
    return 0 if successes > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
