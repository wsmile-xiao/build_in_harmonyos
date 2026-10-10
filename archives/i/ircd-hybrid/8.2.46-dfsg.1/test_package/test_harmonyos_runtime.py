#!/usr/bin/env python3
"""Run ircd-hybrid and an IRC client exchange on the HarmonyOS device."""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def platform_probe():
    # HarmonyOS Python can execute uname by absolute path, but PATH lookup by
    # subprocess may fail in an SSH-launched interpreter. os.uname() avoids
    # that environment-dependent lookup while probing the same kernel value.
    system = os.uname().sysname
    require(system == "HarmonyOS", "expected HarmonyOS kernel, got %r" % system)

    param = shutil.which("param") or "/usr/bin/param"
    result = subprocess.run(
        [param, "get", "const.product.software.version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    version = result.stdout.strip()
    require(result.returncode == 0 and version,
            "HarmonyOS param query failed: %s" % result.stderr.strip())
    print("HARMONYOS_KERNEL=%s" % system)
    print("HARMONYOS_PRODUCT=%s" % version)


def binary_probe(binary, module_dir):
    require(os.path.isfile(binary), "ircd binary missing: %s" % binary)
    require(os.access(binary, os.X_OK), "ircd binary is not executable: %s" % binary)
    version = subprocess.run(
        [binary, "-version"], capture_output=True, text=True, timeout=15
    )
    banner = version.stdout + version.stderr
    require(version.returncode == 0 and "8.2.46" in banner,
            "ircd -version did not report 8.2.46: %s" % banner.strip())

    required_modules = ("m_nick.la", "m_user.la", "m_ping.la", "m_pong.la",
                        "m_quit.la", "m_message.la")
    missing = [name for name in required_modules
               if not os.path.isfile(os.path.join(module_dir, name))]
    require(not missing, "required loadable modules missing: %s" % ", ".join(missing))
    print("IRCD_VERSION=%s" % banner.strip().replace("\n", " | "))
    print("MODULES_PRESENT=%s" % ",".join(required_modules))


def receive_until(sock, marker, deadline):
    data = bytearray()
    while marker not in data:
        if time.monotonic() >= deadline:
            raise RuntimeError("timed out waiting for %r; received %r" %
                               (marker, bytes(data)))
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            raise RuntimeError("connection closed before %r; received %r" %
                               (marker, bytes(data)))
        data.extend(chunk)
        if len(data) > 32768:
            raise RuntimeError("unexpectedly large IRC response")
    return bytes(data)


def runtime_probe(binary, module_dir):
    temp_base = None
    for key in ("TMPDIR", "TMP", "TEMP"):
        candidate = os.environ.get(key)
        if candidate:
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = tempfile.mkdtemp(prefix="ircd-hybrid-write-", dir=candidate)
                os.rmdir(probe)
                temp_base = candidate
                break
            except OSError:
                continue
    work = tempfile.mkdtemp(prefix="ircd-hybrid-ohos-", dir=temp_base or os.getcwd())
    pid = None
    port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_socket.bind(("127.0.0.1", 0))
    port = port_socket.getsockname()[1]
    port_socket.close()

    config = os.path.join(work, "ircd.conf")
    modules = os.path.join(work, "modules.conf")
    logfile = os.path.join(work, "ircd.log")
    pidfile = os.path.join(work, "ircd.pid")
    with open(config, "w", encoding="utf-8") as stream:
        stream.write(
            ".include %s;\n" % json.dumps(modules)
            + "serverinfo {\n"
            '  name = "harmonyos-test.local";\n'
            '  description = "HarmonyOS native integration test";\n'
            '  network_name = "HarmonyOS-Test";\n'
            '  network_description = "Local package test";\n'
            "  hub = no;\n"
            "  default_max_clients = 32;\n"
            "};\n"
            "admin { name = \"Codex test\"; description = \"consumer test\"; "
            'email = "test@localhost"; };\n'
            "class { name = \"users\"; ping_time = 90 seconds; "
            "max_number = 32; sendq = 100 kbytes; };\n"
            "listen { host = \"127.0.0.1\"; port = %d; };\n" % port
            + "auth { user = \"*@*\"; class = \"users\"; };\n"
        )
    with open(modules, "w", encoding="utf-8") as stream:
        stream.write("module_base_path = %s;\n" % json.dumps(module_dir))
        stream.write('loadmodule "m_nick.la" : core;\n')
        stream.write('loadmodule "m_user.la";\n')
        stream.write('loadmodule "m_ping.la";\n')
        stream.write('loadmodule "m_pong.la";\n')
        stream.write('loadmodule "m_quit.la" : core;\n')
        stream.write('loadmodule "m_message.la" : core;\n')

    proc = None
    try:
        proc = subprocess.Popen(
            [binary, "-foreground", "-configfile", config,
             "-logfile", logfile, "-pidfile", pidfile],
            cwd=work,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 25
        connected = None
        last_error = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                connected = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.25)
        if connected is None:
            output = b""
            if proc.poll() is not None and proc.stdout:
                output = proc.stdout.read()
            log = ""
            if os.path.isfile(logfile):
                with open(logfile, "r", encoding="utf-8", errors="replace") as stream:
                    log = stream.read()
            raise RuntimeError(
                "ircd did not listen on 127.0.0.1:%d; error=%r; output=%r; log=%s"
                % (port, last_error, output[-4096:].decode("utf-8", "replace"),
                   log[-4096:])
            )

        with connected:
            connected.settimeout(1)
            connected.sendall(b"NICK codex\r\nUSER codex 0 * :HarmonyOS test\r\n")
            try:
                welcome = receive_until(connected, b" 001 codex ", time.monotonic() + 25)
            except RuntimeError as exc:
                log = ""
                if os.path.isfile(logfile):
                    with open(logfile, "r", encoding="utf-8", errors="replace") as stream:
                        log = stream.read()
                raise RuntimeError("%s; daemon log=%s" % (exc, log[-4096:])) from exc
            connected.sendall(b"PING :harmonyos-probe\r\n")
            pong = receive_until(
                connected, b" PONG harmonyos-test.local :harmonyos-probe",
                time.monotonic() + 12
            )
            connected.sendall(b"QUIT :test complete\r\n")
        require(b"harmonyos-test.local" in welcome,
                "001 welcome did not identify the configured server: %r" % welcome)
        require(b" PONG harmonyos-test.local :harmonyos-probe" in pong,
                "server did not answer IRC PING: %r" % pong)
        print("IRC_WELCOME=%s" % welcome.decode("utf-8", "replace").strip())
        print("IRC_PONG=%s" % pong.decode("utf-8", "replace").strip())

        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            raise RuntimeError("ircd did not stop after SIGTERM")
        require(proc.returncode == 0,
                "ircd exited with %s after SIGTERM" % proc.returncode)
        print("IRCD_EXIT=%s" % proc.returncode)
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        shutil.rmtree(work, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        print("usage: test_harmonyos_runtime.py <ircd> <module-dir>", file=sys.stderr)
        return 2
    binary, module_dir = sys.argv[1:]
    tests = (
        ("HarmonyOS device identity", lambda: platform_probe()),
        ("packaged daemon and modules", lambda: binary_probe(binary, module_dir)),
        ("native dynamic modules and IRC socket exchange",
         lambda: runtime_probe(binary, module_dir)),
    )
    passed = 0
    failed = 0
    for index, (name, test) in enumerate(tests, 1):
        try:
            test()
            print("CASE %d PASS: %s" % (index, name))
            passed += 1
        except Exception as exc:
            print("CASE %d FAIL: %s: %s" % (index, name, exc))
            failed += 1
            # Runtime integration depends on an installed executable and its
            # modules; don't report a second, derivative failure when those
            # package prerequisites are absent.
            if index <= 2:
                break
    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
