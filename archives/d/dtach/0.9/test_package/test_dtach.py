from pathlib import Path
import os
import shutil
import signal
import subprocess
import sys
import time


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def find_master_pid(sock_path):
    """Find the daemonized dtach master holding the socket (via /proc fd links)."""
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        fd_dir = f"/proc/{entry}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(os.path.join(fd_dir, fd)) == sock_path:
                    return int(entry)
            except OSError:
                pass
    return None


def main(binary):
    version = run([binary, "--version"])
    assert version.returncode == 0, version.stderr
    assert "dtach - version 0.9" in version.stdout

    help_out = run([binary, "--help"])
    assert help_out.returncode == 0, help_out.stderr
    assert "Usage: dtach -a <socket> <options>" in help_out.stdout

    # OHOS (musl) only allows binding named unix sockets under
    # /data/storage/el2/base — use a dedicated subdirectory there.
    base = Path("/data/storage/el2/base")
    workdir = base / f"dtach-test-{os.getpid()}-{int(time.time())}"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        tmp = workdir
        sock = tmp / "dtach.sock"
        marker = tmp / "marker.txt"
        worker = tmp / "worker.py"
        worker.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "Path(sys.argv[1]).write_text('dtach-ok')\n"
        )
        # -n: create the socket, run the worker daemonized under a pty, and
        # return immediately. (Upstream dtach 0.9 -N (foreground) mode exits
        # with 1 once the short-lived worker EOFs the pty, so -n is the
        # reliable mode for a smoke test.)
        detached = run([binary, "-n", str(sock), sys.executable, str(worker), str(marker)])
        assert detached.returncode == 0, detached.stderr + detached.stdout
        # The worker is started asynchronously inside the pty; poll for the
        # marker (python startup takes a moment).
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists(), "marker was not written by the dtach worker"
        assert marker.read_text() == "dtach-ok"
    finally:
        # Kill the daemonized master, then remove the workdir (the socket
        # file itself is unlinked by the master via atexit on SIGTERM).
        master_pid = find_master_pid(str(sock))
        if master_pid and master_pid != os.getpid():
            try:
                os.kill(master_pid, signal.SIGTERM)
            except OSError:
                pass
            time.sleep(0.2)
        shutil.rmtree(workdir, ignore_errors=True)

    print("dtach smoke test passed")


if __name__ == "__main__":
    main(sys.argv[1])
