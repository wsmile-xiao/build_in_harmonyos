"""Consume the installed client against an ephemeral, loopback-only FTP fixture."""
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


class FTPFixture:
    def __init__(self):
        self.payload = bytes(range(256)) * 257
        self.files = {"fixture.bin": self.payload}
        self.commands = []
        self.error = None
        self.stop = threading.Event()
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(1)
        self.port = self.listener.getsockname()[1]
        self.worker = threading.Thread(target=self.serve, daemon=True)

    def serve(self):
        passive = None
        try:
            while not self.stop.is_set():
                try:
                    control, peer = self.listener.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
            with control:
                control.settimeout(15)
                stream = control.makefile("rb")

                def reply(value):
                    control.sendall((value + "\r\n").encode("ascii"))

                reply("220 task-local fixture ready")
                while not self.stop.is_set():
                    line = stream.readline(4096)
                    if not line:
                        break
                    verb, _, argument = line.decode("ascii").strip().partition(" ")
                    verb = verb.upper()
                    self.commands.append((verb, argument))
                    name = argument.rsplit("/", 1)[-1]
                    if verb == "USER":
                        reply("331 password required")
                    elif verb == "PASS":
                        reply("230 login successful" if argument == "fixture" else "530 bad login")
                    elif verb == "SYST":
                        reply("215 UNIX Type: L8")
                    elif verb == "PWD":
                        reply('257 "/" is current directory')
                    elif verb in ("TYPE", "CWD", "OPTS", "NOOP", "ALLO"):
                        reply("200 command successful")
                    elif verb in ("PASV", "EPSV"):
                        if passive:
                            passive.close()
                        passive = socket.socket()
                        passive.bind(("127.0.0.1", 0))
                        passive.listen(1)
                        passive.settimeout(10)
                        port = passive.getsockname()[1]
                        reply("229 Entering Extended Passive Mode (|||%d|)" % port if verb == "EPSV"
                              else "227 Entering Passive Mode (127,0,0,1,%d,%d)" % (port // 256, port % 256))
                    elif verb == "SIZE":
                        reply("213 %d" % len(self.files[name]) if name in self.files else "550 not found")
                    elif verb == "MDTM":
                        reply("213 20260101000000" if name in self.files else "550 not found")
                    elif verb in ("LIST", "NLST", "RETR", "STOR"):
                        if not passive:
                            reply("425 passive connection required")
                            continue
                        if verb == "RETR" and name not in self.files:
                            reply("550 not found")
                            continue
                        reply("150 opening data connection")
                        data, _ = passive.accept()
                        passive.close()
                        passive = None
                        with data:
                            data.settimeout(10)
                            if verb == "STOR":
                                chunks = []
                                while True:
                                    block = data.recv(8192)
                                    if not block:
                                        break
                                    chunks.append(block)
                                self.files[name] = b"".join(chunks)
                                self.uploaded = self.files[name]
                            elif verb == "RETR":
                                data.sendall(self.files[name])
                            elif verb == "NLST":
                                data.sendall("".join(n + "\r\n" for n in sorted(self.files)).encode())
                            else:
                                data.sendall("".join("-rw-r--r-- 1 fixture fixture %d Jan 01 00:00 %s\r\n" %
                                                     (len(b), n) for n, b in sorted(self.files.items())).encode())
                        reply("226 transfer complete")
                    elif verb == "DELE":
                        if name in self.files:
                            del self.files[name]
                            reply("250 deleted")
                        else:
                            reply("550 not found")
                    elif verb == "QUIT":
                        reply("221 goodbye")
                        break
                    else:
                        reply("502 unsupported fixture command")
                stream.close()
        except Exception as error:
            if not self.stop.is_set():
                self.error = error
        finally:
            if passive:
                passive.close()

    def close(self):
        self.stop.set()
        self.listener.close()
        self.worker.join(3)
        if self.worker.is_alive():
            raise AssertionError("FTP fixture thread did not exit")
        if self.error:
            raise self.error


def passed(label):
    print("CONSUMER_PASS " + label, flush=True)


binary = Path(sys.argv[1])
assert binary.is_file(), "installed yafc missing"
result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=15, check=True)
assert result.stdout.strip() == "yafc 1.3.7", result.stdout
passed("installed version")
result = subprocess.run([str(binary), "--help"], capture_output=True, text=True, timeout=15, check=True)
assert "--workdir" in result.stdout + result.stderr and "--version" in result.stdout + result.stderr
passed("installed help")
with tempfile.TemporaryDirectory(prefix="yafc-consumer-", dir=Path.cwd()) as temporary:
    root = Path(temporary)
    payload = bytes(range(256)) * 257
    (root / "upload.bin").write_bytes(payload[::-1])
    fixture = FTPFixture()
    fixture.worker.start()
    try:
        commands = "set passive on\nls\nget --type=binary -f -o downloaded.bin fixture.bin\nput --type=binary -o uploaded.bin upload.bin\nrm -f uploaded.bin\nquit\n"
        result = subprocess.run([str(binary), "-n", "-U", "-p", "-q", "-W", str(root / "config"),
                                 "ftp://fixture:fixture@127.0.0.1:%d/" % fixture.port],
                                input=commands, cwd=root, capture_output=True, text=True, timeout=60)
        print(result.stdout, end="", flush=True)
        print(result.stderr, end="", file=sys.stderr, flush=True)
        assert result.returncode == 0, result.returncode
        transcript = fixture.commands
        assert ("PASS", "fixture") in transcript and any(v in ("LIST", "NLST") for v, _ in transcript)
        assert "fixture.bin" in result.stdout
        passed("FTP login and directory listing")
        assert (root / "downloaded.bin").read_bytes() == payload
        assert any(v == "RETR" and a.endswith("fixture.bin") for v, a in transcript)
        passed("FTP binary download")
        # Server captures uploaded bytes before deletion for a content assertion.
        assert fixture.files.get("uploaded.bin") is None
        assert any(v == "STOR" and a.endswith("uploaded.bin") for v, a in transcript)
        # A second independent download would cost another server session;
        # retain the actual STOR byte stream as part of this fixture instead.
        assert getattr(fixture, "uploaded", None) == payload[::-1]
        passed("FTP binary upload")
        assert any(v == "DELE" and a.endswith("uploaded.bin") for v, a in transcript)
        passed("FTP remote deletion")
    finally:
        fixture.close()
