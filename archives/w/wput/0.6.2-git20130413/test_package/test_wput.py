#!/usr/bin/env python3
"""HarmonyOS consumer test: run Wput and upload a fixture to loopback FTP."""

import os
import platform
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading


class FTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.passive_listener = None
        self.wfile.write(b"220 Wput HarmonyOS loopback test\r\n")
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            command, _, argument = raw.decode("ascii", "replace").rstrip("\r\n").partition(" ")
            command = command.upper()
            if command == "USER":
                self.reply("331 Password required")
            elif command == "PASS":
                self.reply("230 Login successful")
            elif command == "SYST":
                self.reply("215 UNIX Type: L8")
            elif command == "FEAT":
                self.reply("211 End")
            elif command == "PWD":
                self.reply('257 "/" is the current directory')
            elif command == "CWD":
                self.reply("250 Directory changed")
            elif command == "TYPE":
                self.reply("200 Type set")
            elif command in ("SIZE", "MDTM"):
                self.reply("550 File not found")
            elif command == "PASV":
                self.open_passive_listener()
            elif command == "STOR":
                self.store_file(argument)
            elif command == "NOOP":
                self.reply("200 OK")
            elif command == "QUIT":
                self.reply("221 Goodbye")
                return
            else:
                self.reply("500 Unsupported command")

    def reply(self, message):
        self.wfile.write((message + "\r\n").encode("ascii"))

    def open_passive_listener(self):
        if self.passive_listener is not None:
            self.passive_listener.close()
        self.passive_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.passive_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.passive_listener.bind(("127.0.0.1", 0))
        self.passive_listener.listen(1)
        port = self.passive_listener.getsockname()[1]
        self.reply("227 Entering Passive Mode (127,0,0,1,%d,%d)" % (port >> 8, port & 255))

    def store_file(self, filename):
        self.reply("150 Ready to receive data")
        data, _ = self.passive_listener.accept()
        self.passive_listener.close()
        self.passive_listener = None
        chunks = []
        with data:
            while True:
                chunk = data.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        self.server.files[filename.rsplit("/", 1)[-1]] = b"".join(chunks)
        self.reply("226 Transfer complete")


class FTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.files = {}


def main(binary):
    if platform.system() != "HarmonyOS":
        raise AssertionError("native target must report HarmonyOS, got %s" % platform.system())
    if platform.machine() not in ("aarch64", "arm64"):
        raise AssertionError("expected an AArch64 HarmonyOS target, got %s" % platform.machine())

    version = subprocess.run(
        [binary, "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=10,
    )
    if version.returncode != 0 or "0.6.2" not in version.stdout:
        raise AssertionError("wput --version failed or reported the wrong version: %s" % version.stdout)

    server = FTPServer(("127.0.0.1", 0), FTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="wput-test-") as directory:
            payload = b"wput HarmonyOS loopback upload\n\x00\xff"
            local_file = os.path.join(directory, "fixture.bin")
            with open(local_file, "wb") as stream:
                stream.write(payload)
            port = server.server_address[1]
            url = "ftp://test:secret@127.0.0.1:%d/fixture.bin" % port
            upload = subprocess.run(
                [binary, "--quiet", "--binary", local_file, url],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
            )
            if upload.returncode != 0:
                raise AssertionError("wput upload failed (%d): %s" % (upload.returncode, upload.stdout))
            received = server.files.get("fixture.bin")
            if received != payload:
                raise AssertionError("loopback FTP server did not receive the exact fixture bytes")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)

    print("PASS: HarmonyOS AArch64 execution and FTP upload")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_wput.py /path/to/wput")
    main(sys.argv[1])
