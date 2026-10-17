#!/usr/bin/env python3
"""Live DNS service assertions for the packaged yaku-ns daemon (7 assertions).

Starts the *packaged* ``bin/yaku-ns`` as a real daemon on a loopback high port
with a generated zone and then speaks DNS to it:

  1. the daemon starts and keeps running
  2. A query for www.example.com resolves to the configured 192.0.2.10
  3. A query for a name outside the zone is answered with NXDOMAIN (rcode 3)
  4. MX for the zone returns preference 10 and mail.example.com
  5. TXT for the zone returns the configured text
  6. NS for the zone returns ns.example.com
  7. a TCP (length-prefixed) SOA query returns the zone SOA record

Every response is parsed here rather than pattern-matched against the daemon's
log, so these assertions fail if the wire format is wrong even when the daemon
believes it answered.

Why UDP plus TCP SOA and not a full AXFR transfer: upstream's send_zone() has an
off-by-one in its has-table walk (``index++`` before ``ht_value()``) that crashes
the forked child with SIGSEGV.  That reproduces identically on a native x86-64
glibc build, so it is an upstream defect rather than a porting problem, and
patches/0002 deliberately leaves it alone.  The TCP SOA path exercises the same
AXFR server socket without entering the buggy loop.
"""

import os
import pwd
import shutil
import socket
import struct
import subprocess
import sys
import time

ASSERTIONS = 7

T_A, T_NS, T_SOA, T_MX, T_TXT = 1, 2, 6, 15, 16
RCODE_NOERROR, RCODE_NXDOMAIN = 0, 3

ZONE = """loglevel errors
SOA example.com ns.example.com hostmaster.example.com 2026100301 3600 600 86400 3600
A www.example.com 192.0.2.10
A mail.example.com 192.0.2.20
MX example.com 10 mail.example.com
TXT example.com v=spf1 -all
NS example.com ns.example.com
"""


def check(index, description, condition, detail=""):
    if condition:
        print("PASS [%d/%d] %s" % (index, ASSERTIONS, description))
        return 0
    print("FAIL [%d/%d] %s" % (index, ASSERTIONS, description))
    if detail:
        print(detail)
    return 1


def encode_name(name):
    out = b""
    for label in name.split("."):
        if label:
            out += bytes([len(label)]) + label.encode("ascii")
    return out + b"\x00"


def build_query(name, qtype, ident=0x4A11):
    header = struct.pack(">HHHHHH", ident, 0x0100, 1, 0, 0, 0)
    return header + encode_name(name) + struct.pack(">HH", qtype, 1)


def decode_name(data, offset):
    labels = []
    while True:
        if offset >= len(data):
            raise ValueError("truncated name at offset %d" % offset)
        length = data[offset]
        offset += 1
        if length == 0:
            break
        if length & 0xC0:  # compression pointer: not produced by yaku-ns
            raise ValueError("unexpected compression pointer")
        labels.append(data[offset:offset + length].decode("ascii"))
        offset += length
    return ".".join(labels), offset


def decode_answers(data, expect_qtype=None):
    """Return (rcode, [(owner, rtype, rdata)]) for a response packet."""
    if len(data) < 12:
        raise ValueError("response shorter than a DNS header")
    flags = struct.unpack_from(">H", data, 2)[0]
    rcode = flags & 0x0F
    ancount = struct.unpack_from(">H", data, 6)[0]
    _, offset = decode_name(data, 12)
    qtype, qclass = struct.unpack_from(">HH", data, offset)
    offset += 4
    # yaku-ns echoes the question verbatim, so QCLASS must be IN and QTYPE must
    # be whatever was asked.  Both are checked so a response to the wrong
    # question cannot be mistaken for the right one.
    if qclass != 1:
        raise ValueError("question class is not IN: %d" % qclass)
    if expect_qtype is not None and qtype != expect_qtype:
        raise ValueError("question type is %d, expected %d" % (qtype, expect_qtype))
    answers = []
    for _ in range(ancount):
        owner, offset = decode_name(data, offset)
        rtype, _rclass, _ttl, rdlength = struct.unpack_from(">HHIH", data, offset)
        offset += 10
        answers.append((owner, rtype, data[offset:offset + rdlength]))
        offset += rdlength
    return rcode, answers


def reserve_port():
    """Pick a free loopback UDP port for the daemon."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def daemon_user():
    """Account name to hand to -u, or None.

    yaku-ns only drops privileges when it starts as root, and it resolves -u
    with getpwnam() and exits 1 when that lookup fails.  Passing the name that
    owns the current uid keeps the lookup satisfiable on hosts whose /etc/passwd
    has no 'nobody' entry.
    """
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return None


def udp_query(sock, name, qtype, port):
    sock.sendto(build_query(name, qtype), ("127.0.0.1", port))
    data, _ = sock.recvfrom(4096)
    return decode_answers(data, expect_qtype=qtype)


def tcp_soa(port, name):
    conn = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        query = build_query(name, T_SOA)
        conn.sendall(struct.pack(">H", len(query)) + query)
        header = b""
        while len(header) < 2:
            chunk = conn.recv(2 - len(header))
            if not chunk:
                raise ValueError("connection closed before the length prefix")
            header += chunk
        length = struct.unpack(">H", header)[0]
        body = b""
        while len(body) < length:
            chunk = conn.recv(length - len(body))
            if not chunk:
                raise ValueError("connection closed inside the DNS message")
            body += chunk
        return decode_answers(body, expect_qtype=T_SOA)
    finally:
        conn.close()


def main():
    daemon, workdir = sys.argv[1], sys.argv[2]
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)

    # yaku-ns chdir()s to "/" before reading its configuration, so -c has to be
    # an absolute path even though the test itself runs in workdir.
    conf_path = os.path.join(workdir, "yaku-ns.conf")
    with open(conf_path, "w", encoding="utf-8") as fh:
        fh.write(ZONE)
    log_path = os.path.join(workdir, "yaku-ns.log")

    port = reserve_port()
    argv = [daemon, "-x", "-b", "127.0.0.1",
            "-p", str(port), "-P", str(port), "-c", conf_path]
    user = daemon_user()
    if user:
        argv += ["-u", user]
    print("launching: %s" % " ".join(argv))

    logfile = open(log_path, "wb")
    try:
        proc = subprocess.Popen(argv, stdout=logfile, stderr=subprocess.STDOUT)
    finally:
        logfile.close()

    failures = 0
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)

        # Wait for the socket to come up by retrying the first real query.
        deadline = time.time() + 20
        rcode = answers = None
        last_error = None
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                rcode, answers = udp_query(sock, "www.example.com", T_A, port)
                break
            except (socket.timeout, OSError, ValueError) as exc:
                last_error = exc
                time.sleep(0.25)

        if proc.poll() is not None:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                failures += check(
                    1, "the packaged daemon starts and keeps running", False,
                    "exited with %s\n%s" % (proc.returncode, fh.read()))
        elif rcode is None:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                failures += check(
                    1, "the packaged daemon starts and keeps running", False,
                    "no answer within the timeout (%s)\n%s"
                    % (last_error, fh.read()))
        else:
            failures += check(1, "the packaged daemon starts and keeps running", True)

        def log_tail():
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                return fh.read()[-2000:]

        # Assertion 2 is served by the readiness query above; if the daemon died
        # the remaining queries cannot work either, so report them as failures
        # with the log instead of raising.
        expected = socket.inet_aton("192.0.2.10")
        failures += check(
            2, "A www.example.com resolves to the configured 192.0.2.10",
            answers is not None and len(answers) == 1
            and answers[0][1] == T_A and answers[0][2] == expected,
            "answers=%r\n%s" % (answers, log_tail() if answers is None else ""))

        if answers is not None:
            nx_rcode, nx_answers = udp_query(sock, "absent.example.com", T_A, port)
            failures += check(
                3, "a name outside the zone is answered with NXDOMAIN",
                nx_rcode == RCODE_NXDOMAIN and not nx_answers,
                "rcode=%r answers=%r" % (nx_rcode, nx_answers))

            _, mx = udp_query(sock, "example.com", T_MX, port)
            mx_ok = (len(mx) == 1 and mx[0][1] == T_MX
                     and struct.unpack(">H", mx[0][2][:2])[0] == 10
                     and mx[0][2][2:] == encode_name("mail.example.com"))
            failures += check(
                4, "MX for the zone returns preference 10 and mail.example.com",
                mx_ok, "answers=%r" % (mx,))

            _, txt = udp_query(sock, "example.com", T_TXT, port)
            txt_ok = (len(txt) == 1 and txt[0][1] == T_TXT
                      and txt[0][2][1:] == b"v=spf1 -all")
            failures += check(
                5, "TXT for the zone returns the configured text",
                txt_ok, "answers=%r" % (txt,))

            _, ns = udp_query(sock, "example.com", T_NS, port)
            ns_ok = (len(ns) == 1 and ns[0][1] == T_NS
                     and ns[0][2] == encode_name("ns.example.com"))
            failures += check(
                6, "NS for the zone returns ns.example.com",
                ns_ok, "answers=%r" % (ns,))

            soa_rcode, soa = tcp_soa(port, "example.com")
            # SOA rdata is: primary NS name, responsible mailbox name, then five
            # 32-bit timers.  Both names are checked; the trailing fixed-size
            # timer block is not, because its layout is upstream's business.
            soa_rdata = soa[0][2] if soa else b""
            soa_ok = (soa_rcode == RCODE_NOERROR and len(soa) == 1
                      and soa[0][1] == T_SOA
                      and soa_rdata.startswith(encode_name("ns.example.com"))
                      and encode_name("hostmaster.example.com") in soa_rdata)
            failures += check(
                7, "a TCP SOA query returns the zone SOA record",
                soa_ok, "rcode=%r answers=%r" % (soa_rcode, soa))
        else:
            for index, description in (
                (3, "a name outside the zone is answered with NXDOMAIN"),
                (4, "MX for the zone returns preference 10 and mail.example.com"),
                (5, "TXT for the zone returns the configured text"),
                (6, "NS for the zone returns ns.example.com"),
                (7, "a TCP SOA query returns the zone SOA record"),
            ):
                failures += check(index, description, False,
                                  "skipped: the daemon never answered")
    finally:
        if sock is not None:
            sock.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)

    if failures:
        print("test_dns_service: %d/%d assertions FAILED" % (failures, ASSERTIONS))
        return 1
    print("test_dns_service: %d/%d assertions passed" % (ASSERTIONS, ASSERTIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
