#!/usr/bin/env python3
"""Consumer test for the pazpar2 Conan package (HarmonyOS PC).

Three groups of assertions:

  H — HarmonyOS platform facts about the produced binary
      H1 ELF64 / little endian / AArch64 (0xB7)
      H2 the interpreter is musl (`/lib/ld-musl-aarch64.so.1`)
      H3 no separate libpthread/libdl/librt DT_NEEDED (musl folds them into libc)
  C — functional end-to-end checks driving the installed daemon
      C1  `pazpar2 -V` reports the version
      C2  `pazpar2 -V` reports the YAZ it was linked against
      C3  the daemon starts and binds a loopback port
      C4  `command=init&service=<id>` establishes a session
      C5  `command=search` returns OK
      C6  pazpar2 issues a real searchRetrieve request to the SRU target
      C7  `command=show` aggregates the target hit
      C8  the record is normalised through libxslt (`<md-title>` rendered)
      C9  `command=ping` answers on the session
      C10 the daemon terminates cleanly on SIGTERM
  P — HarmonyOS PC packaging facts
      P1  third-party DT_NEEDED is only libxml2.so.16 (yaz/libxslt are static)
      P2  RUNPATH resolves libxml2.so.16 offline (no env needed at run time)

Only the standard library is used so the test runs inside the conanrun
environment without extra requirements.
"""
import http.server
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

VERSION = "1.14.1"
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         (" (" + detail + ")") if detail else ""), flush=True)
    return bool(ok)


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def elf_info(path):
    """Minimal, dependency-free ELF reader (machine/interp/NEEDED/RUNPATH)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        return None
    is64 = data[4] == 2
    endian = "<" if data[5] == 1 else ">"
    machine = struct.unpack_from(endian + "H", data, 18)[0]
    if is64:
        phoff = struct.unpack_from(endian + "Q", data, 32)[0]
        phentsize = struct.unpack_from(endian + "H", data, 54)[0]
        phnum = struct.unpack_from(endian + "H", data, 56)[0]
    else:
        phoff = struct.unpack_from(endian + "I", data, 28)[0]
        phentsize = struct.unpack_from(endian + "H", data, 42)[0]
        phnum = struct.unpack_from(endian + "H", data, 44)[0]
    loads, dynamic, interp = [], None, ""
    for i in range(phnum):
        off = phoff + i * phentsize
        if is64:
            p_type, _flags, p_off, p_vaddr, _paddr, p_filesz = struct.unpack_from(
                endian + "IIQQQQ", data, off)[:6]
        else:
            p_type, p_off, p_vaddr, _paddr, p_filesz = struct.unpack_from(
                endian + "IIIIII", data, off)[:5]
        if p_type == 1:
            loads.append((p_vaddr, p_off, p_filesz))
        elif p_type == 2:
            dynamic = (p_off, p_filesz)
        elif p_type == 3:
            interp = data[p_off:p_off + p_filesz].split(b"\x00")[0].decode()
    needed, paths = [], []
    if dynamic:
        step = 16 if is64 else 8
        fmt = endian + ("qQ" if is64 else "iI")
        entries = [struct.unpack_from(fmt, data, dynamic[0] + i * step)
                   for i in range(dynamic[1] // step)]
        strtab_vaddr = next((v for t, v in entries if t == 5), None)
        strtab_off = None
        for vaddr, off, filesz in loads:
            if strtab_vaddr is not None and vaddr <= strtab_vaddr < vaddr + filesz:
                strtab_off = off + (strtab_vaddr - vaddr)
                break

        def str_at(idx):
            if strtab_off is None:
                return ""
            end = data.index(b"\x00", strtab_off + idx)
            return data[strtab_off + idx:end].decode("utf-8", "replace")

        for tag, val in entries:
            if tag == 1:
                needed.append(str_at(val))
            elif tag in (15, 29):
                paths.extend(p for p in str_at(val).split(":") if p)
    return {"bits": 64 if is64 else 32, "little_endian": endian == "<",
            "machine": machine, "interp": interp, "needed": needed,
            "runpath": paths}


SRU_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
  <version>1.1</version>
  <numberOfRecords>1</numberOfRecords>
  <records>
    <record>
      <recordSchema>info:srw/schema/1/dc-v1.1</recordSchema>
      <recordData>
        <dc xmlns="http://purl.org/dc/elements/1.1/">
          <identifier>rec-0001</identifier>
          <title>Computer networks</title>
          <creator>Jane Doe</creator>
          <date>2020</date>
        </dc>
      </recordData>
    </record>
  </records>
</searchRetrieveResponse>
"""


class MockSRU(http.server.BaseHTTPRequestHandler):
    """Minimal SRU 1.1 endpoint used as the Z39.50/SRU target of pazpar2."""

    seen = []

    def do_GET(self):
        MockSRU.seen.append(self.path)
        body = SRU_DOC.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


PZ2_XSLT = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:pz="http://www.indexdata.com/pazpar2/1.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/">
  <xsl:output method="xml" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <pz:record>
      <pz:metadata type="id"><xsl:value-of select="//dc:identifier"/></pz:metadata>
      <pz:metadata type="title"><xsl:value-of select="//dc:title"/></pz:metadata>
      <pz:metadata type="author"><xsl:value-of select="//dc:creator"/></pz:metadata>
      <pz:metadata type="date"><xsl:value-of select="//dc:date"/></pz:metadata>
    </pz:record>
  </xsl:template>
</xsl:stylesheet>
"""

PZ2_CFG = """<?xml version="1.0" encoding="UTF-8"?>
<pazpar2 xmlns="http://www.indexdata.com/pazpar2/1.0">
  <server>
    <listen port="{pz2_port}"/>
    <service id="mock">
      <settings target="127.0.0.1:{sru_port}/sru">
        <set name="pz:name" value="mock-sru"/>
        <set name="pz:sru" value="get"/>
        <set name="pz:url" value="127.0.0.1:{sru_port}/sru"/>
        <set name="pz:nativesyntax" value="xml"/>
        <set name="pz:xslt" value="mock2pz.xsl"/>
      </settings>
      <metadata name="id"/>
      <metadata name="title" brief="yes"/>
      <metadata name="author" termlist="yes"/>
      <metadata name="date"/>
    </service>
  </server>
</pazpar2>
"""


def get(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def wait_port(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def platform_checks(binary):
    info = elf_info(binary)
    if info is None:
        check("H1 ELF64/AArch64 binary", False, "not an ELF file")
        return
    check("H1 ELF64 little-endian AArch64 binary",
          info["bits"] == 64 and info["little_endian"] and info["machine"] == 0xB7,
          "class=%d bit, e_machine=0x%X" % (info["bits"], info["machine"]))
    check("H2 interpreter is the OHOS musl loader",
          info["interp"] == "/lib/ld-musl-aarch64.so.1", info["interp"])
    split = [n for n in info["needed"]
             if n.startswith(("libpthread.so", "libdl.so", "librt.so"))]
    check("H3 no separate libpthread/libdl/librt dependency (musl folds them into libc)",
          not split, "NEEDED=%s" % ",".join(info["needed"]))
    check("P1 third-party runtime dependency is only libxml2",
          "libc.so" in info["needed"]
          and set(info["needed"]) <= {"libc.so", "libxml2.so.16"},
          "NEEDED=%s" % ",".join(info["needed"]))
    check("P2 RUNPATH resolves libxml2.so.16 offline",
          any(os.path.exists(os.path.join(d, "libxml2.so.16"))
              for d in info["runpath"]),
          "RUNPATH=%s" % ":".join(info["runpath"]))


def main():
    binary = shutil.which("pazpar2")
    if not binary:
        print("FAIL precondition: pazpar2 not found on PATH")
        return 1
    print("precondition: binary on PATH (%s)" % binary, flush=True)

    platform_checks(binary)

    # ---- C1/C2: version banner ----------------------------------------
    out = subprocess.run([binary, "-V"], capture_output=True, text=True)
    check("C1 pazpar2 -V reports version %s" % VERSION,
          out.returncode == 0 and "Pazpar2 %s" % VERSION in out.stdout,
          out.stdout.strip().replace("\n", " | "))
    check("C2 pazpar2 -V reports the YAZ runtime",
          "yaz:" in out.stdout,
          out.stdout.strip().splitlines()[-1] if out.stdout else "")

    workdir = tempfile.mkdtemp(prefix="pazpar2-test-")
    pz2_port = free_port()
    sru_port = free_port()
    with open(os.path.join(workdir, "pazpar2.xml"), "w") as fh:
        fh.write(PZ2_CFG.format(pz2_port=pz2_port, sru_port=sru_port))
    with open(os.path.join(workdir, "mock2pz.xsl"), "w") as fh:
        fh.write(PZ2_XSLT)

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", sru_port), MockSRU)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    log = open(os.path.join(workdir, "pazpar2.log"), "wb")
    proc = subprocess.Popen(
        [binary, "-f", "pazpar2.xml", "-l", "pazpar2.log", "-X",
         "-v", "loglevel,warn,error"],
        cwd=workdir, stdout=log, stderr=subprocess.STDOUT)
    try:
        # ---- C3: daemon startup ---------------------------------------
        check("C3 daemon binds its loopback port", wait_port(pz2_port),
              "pid=%s port=%s" % (proc.pid, pz2_port))
        base = "http://127.0.0.1:%d/search.pz2" % pz2_port

        # ---- C4: session init -----------------------------------------
        init = get(base + "?command=init&service=mock")
        check("C4 command=init establishes a session",
              "<status>OK</status>" in init and "<session>1</session>" in init
              and "<protocol>1</protocol>" in init,
              init.strip().replace("\n", ""))

        # ---- C5/C6: search reaches the SRU target ---------------------
        search = get(base + "?session=1&command=search&query=computer&maxrecs=3")
        deadline = time.time() + 20
        while time.time() < deadline and not MockSRU.seen:
            time.sleep(0.2)
        sru_req = MockSRU.seen[-1] if MockSRU.seen else ""
        check("C5 command=search returns OK",
              "<status>OK</status>" in search, search.strip().replace("\n", ""))
        check("C6 pazpar2 queried the SRU target",
              "operation=searchRetrieve" in sru_req and "query=computer" in sru_req,
              sru_req)

        # ---- C7/C8: aggregation + libxslt normalisation ---------------
        show = ""
        deadline = time.time() + 30
        while time.time() < deadline:
            show = get(base + "?session=1&command=show&block=1")
            if "<md-title>Computer networks</md-title>" in show:
                break
            time.sleep(0.5)
        check("C7 command=show aggregates the target hit",
              "<status>OK</status>" in show and "<merged>1</merged>" in show
              and "<total>1</total>" in show and "127.0.0.1:%d/sru" % sru_port in show,
              show.strip().replace("\n", " ")[:200])
        check("C8 record normalised through libxslt metadata mapping",
              "<md-title>Computer networks</md-title>" in show,
              "<md-title> rendered" if "<md-title>" in show else "no md-* metadata")

        # ---- C9: ping --------------------------------------------------
        ping = get(base + "?session=1&command=ping")
        check("C9 command=ping answers on the session",
              "<ping>" in ping and "<status>OK</status>" in ping,
              ping.strip().replace("\n", ""))
    finally:
        # ---- C10: clean shutdown --------------------------------------
        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = None
        check("C10 daemon terminates on SIGTERM", rc is not None,
              "exit code %s" % rc)
        log.close()
        httpd.shutdown()

    failed = [name for name, ok, _ in CHECKS if not ok]
    print("\n%d/%d checks passed" % (len(CHECKS) - len(failed), len(CHECKS)),
          flush=True)
    if failed:
        print("failed: " + ", ".join(failed), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
