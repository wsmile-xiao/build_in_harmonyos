#!/usr/bin/env python3
"""Interactive SKK server protocol session against the packaged dbskkd-cdb.

usage: session_check.py <packaged dbskkd-cdb> <dictionary .cdb> <argv|env>

The other consumer cases start one server process per request, which never
exercises the request loop itself. This driver keeps ONE server process alive
and exchanges a sequence of SKK server protocol requests with it (one request,
one answer, in order), then closes the session with the CLIENT_END request and
checks the exit status. Every answer is compared byte for byte against the
response the protocol defines:

  '2'                -> "dbskkd-cdb-3.00 "            (16 bytes, VERSION)
  '3'                -> "novalue: "                    (9 bytes, dummy host)
  '1<key> '          -> "1" + data + "\\n"             (found)
  '1<key> '          -> "4" + key + "\\n"              (not found)
  '0'                -> process exits 0 without output

Results are printed as "CHECK|<name>|<OK|FAIL>|<detail>" lines to stdout, one
per check, and the exit status is 0 only when every check passed. test.sh
parses those lines so that both harnesses keep a single case counter.
"""
import os
import select
import subprocess
import sys

VERSION_ANSWER = "dbskkd-cdb-3.00 ".encode("utf-8")
HOST_ANSWER = "novalue: ".encode("utf-8")

TIMEOUT = 60.0


class Session:
    def __init__(self, binary, dictionary, mode):
        env = os.environ.copy()
        if mode == "env":
            env["DBSKKD_JISYO"] = dictionary
            args = [binary]
        else:
            env.pop("DBSKKD_JISYO", None)
            args = [binary, dictionary]
        self.proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env,
        )

    def send(self, payload):
        self.proc.stdin.write(payload)
        self.proc.stdin.flush()

    def read_exact(self, count):
        chunks = []
        remaining = count
        while remaining > 0:
            ready, _, _ = select.select([self.proc.stdout], [], [], TIMEOUT)
            if not ready:
                raise TimeoutError(
                    "no answer within %.0fs (%d of %d bytes read)"
                    % (TIMEOUT, count - remaining, count)
                )
            chunk = self.proc.stdout.read(remaining)
            if not chunk:
                raise EOFError(
                    "server closed the connection after %d of %d bytes"
                    % (count - remaining, count)
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def wait(self):
        """Wait for the server to exit; None when it had to be killed."""
        try:
            return self.proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            return None

    def shutdown(self):
        self.wait()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except OSError:
                pass


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    binary, dictionary, mode = argv[1], argv[2], argv[3]
    if mode not in ("argv", "env"):
        raise SystemExit("mode must be argv or env")

    checks = []
    session = Session(binary, dictionary, mode)

    def check(name, condition, detail):
        checks.append(bool(condition))
        print("CHECK|%s|%s|%s" % (name, "OK" if condition else "FAIL", detail))

    try:
        # 1. VERSION request: the answer identifies the upstream release.
        session.send(b"2")
        answer = session.read_exact(len(VERSION_ANSWER))
        check("session_version_request", answer == VERSION_ANSWER,
              "answer=%r" % answer)

        # 2. HOST request: constant dummy host name.
        session.send(b"3")
        answer = session.read_exact(len(HOST_ANSWER))
        check("session_host_request", answer == HOST_ANSWER,
              "answer=%r" % answer)

        # 3. A lookup that hits the dictionary.
        key = "かんじ"
        expected = "1/漢字/\n".encode("utf-8")
        session.send(("1" + key + " ").encode("utf-8"))
        answer = session.read_exact(len(expected))
        check("session_lookup_found", answer == expected, "answer=%r" % answer)

        # 4. A lookup that misses: the answer echoes the key (skkinput needs it).
        key = "not-in-dictionary"
        expected = ("4" + key + "\n").encode("utf-8")
        session.send(("1" + key + " ").encode("utf-8"))
        answer = session.read_exact(len(expected))
        check("session_lookup_not_found", answer == expected, "answer=%r" % answer)

        # 5. The loop keeps serving requests after a miss.
        key = "みず"
        expected = "1/水/\n".encode("utf-8")
        session.send(("1" + key + " ").encode("utf-8"))
        answer = session.read_exact(len(expected))
        check("session_lookup_after_miss", answer == expected, "answer=%r" % answer)

        # 6. CLIENT_END: clean shutdown with no further output.
        session.send(b"0")
        rc = session.wait()
        leftover = session.proc.stdout.read() or b""
        check("session_end_request_exit", rc == 0 and leftover == b"",
              "rc=%r leftover=%r" % (rc, leftover))
    except (TimeoutError, EOFError, OSError) as exc:
        check("session_protocol", False, "%s: %s" % (type(exc).__name__, exc))
    finally:
        session.shutdown()

    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
