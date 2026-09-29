"""Local, dependency-free SMTP relay smoke test for the packaged proxsmtpd."""

import os
import smtplib
import socket
import subprocess
import sys
import tempfile
import threading
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def smtp_backend(listener, result):
    try:
        listener.settimeout(12)
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(12)
            stream = connection.makefile("rwb", buffering=0)
            stream.write(b"220 local-test ESMTP\r\n")
            in_data = False
            content = []
            while True:
                line = stream.readline()
                if not line:
                    break
                command = line.strip()
                if in_data:
                    if command == b".":
                        result["body"] = b"\n".join(content)
                        stream.write(b"250 accepted\r\n")
                        in_data = False
                    else:
                        content.append(command)
                elif command.upper().startswith((b"EHLO ", b"HELO ")):
                    stream.write(b"250 local-test\r\n")
                elif command.upper().startswith((b"MAIL FROM:", b"RCPT TO:")):
                    stream.write(b"250 ok\r\n")
                elif command.upper() == b"DATA":
                    stream.write(b"354 send data\r\n")
                    in_data = True
                elif command.upper() == b"QUIT":
                    stream.write(b"221 bye\r\n")
                    break
                else:
                    stream.write(b"250 ok\r\n")
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        listener.close()


def main(binary):
    version = subprocess.check_output([binary, "-v"], text=True)
    assert "1.10" in version, version
    backend_port = free_port()
    front_port = free_port()
    with socket.socket() as backend:
        backend.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        backend.bind(("127.0.0.1", backend_port))
        backend.listen(1)
        result = {}
        worker = threading.Thread(target=smtp_backend, args=(backend, result))
        worker.start()
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as work:
            config = os.path.join(work, "proxsmtpd.conf")
            with open(config, "w", encoding="ascii") as handle:
                handle.write(
                    "Listen: 127.0.0.1:{0}\n"
                    "OutAddress: 127.0.0.1:{1}\n"
                    "TempDirectory: {2}\n"
                    "TimeOut: 5\n".format(front_port, backend_port, work)
                )
            proxy = subprocess.Popen(
                [binary, "-d", "4", "-f", config],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                error = None
                for _ in range(40):
                    if proxy.poll() is not None:
                        raise RuntimeError("proxy exited: " + proxy.stderr.read())
                    try:
                        with smtplib.SMTP("127.0.0.1", front_port, timeout=3) as client:
                            client.sendmail(
                                "sender@example.invalid",
                                ["recipient@example.invalid"],
                                "Subject: smoke\r\n\r\nhello proxsmtp\r\n",
                            )
                        error = None
                        break
                    except (OSError, smtplib.SMTPException) as exc:
                        error = exc
                        time.sleep(0.1)
                if error is not None:
                    raise error
            finally:
                proxy.terminate()
                try:
                    proxy.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proxy.kill()
                    proxy.communicate(timeout=5)
        worker.join(timeout=12)
        assert not worker.is_alive(), "backend did not finish"
        assert "error" not in result, result
        assert b"hello proxsmtp" in result.get("body", b""), result
    print("PASS: installed version and loopback SMTP relay")


if __name__ == "__main__":
    main(sys.argv[1])
