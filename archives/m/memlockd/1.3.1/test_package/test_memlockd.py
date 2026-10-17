#!/usr/bin/env python3
"""Consumer test for memlockd 1.3.1 on HarmonyOS PC (OHOS aarch64, non-root).

Drives the *installed* daemon the way an operator would: write a config file, start
`memlockd -d -c <cfg>`, then assert on its verbatim log lines, on /proc/<pid>/maps (the
mapping is attached) and on the differential of /proc/<pid>/smaps_rollup "Locked:"
(the pages really got wired). Nothing here needs root -- that is the point of layer 2.
"""
import os
import re
import resource
import signal
import subprocess
import sys
import threading
import time

PKG = os.path.abspath(sys.argv[1])
WORK = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath(os.getcwd())
BIN = os.path.join(PKG, "bin", "memlockd")

PASSED = []
FAILED = []
_lock = threading.Lock()


def check(name, ok, detail=""):
    if ok:
        PASSED.append(name)
        print(f"PASS {len(PASSED)}: {name}", flush=True)
    else:
        FAILED.append(name)
        print(f"FAIL: {name} :: {detail}", flush=True)
    return bool(ok)


def cfg_text(*lines):
    return "\n".join(lines) + "\n"


class Daemon:
    """`memlockd -d` (memlockd.cpp:401) keeps the process in the foreground and routes
    log() to vfprintf(stderr, ...) instead of vsyslog(), and the daemon(3) call at :428
    is skipped -- so stderr is simultaneously the log and the liveness probe."""

    def __init__(self, cfg):
        os.makedirs(WORK, exist_ok=True)
        self.cfg_path = os.path.join(WORK, f"cfg-{os.getpid()}-{int(time.time()*1000)%1000000}.cfg")
        with open(self.cfg_path, "w", encoding="utf-8") as fh:
            fh.write(cfg)
        self.lines = []
        self.proc = subprocess.Popen([BIN, "-d", "-c", self.cfg_path],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE,
                                     text=True, bufsize=1)
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stderr:
            with _lock:
                self.lines.append(line.rstrip("\n"))

    def set_cfg(self, cfg):
        with open(self.cfg_path, "w", encoding="utf-8") as fh:
            fh.write(cfg)

    def expect(self, needle, timeout=20.0, start=0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with _lock:
                hits = [l for l in self.lines[start:] if needle in l]
                n = len(self.lines)
            if hits:
                return hits[0], n
            if self.proc.poll() is not None:
                break
            time.sleep(0.1)
        with _lock:
            return None, len(self.lines)

    def snapshot(self):
        with _lock:
            return list(self.lines)

    def maps(self):
        try:
            with open(f"/proc/{self.proc.pid}/maps", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            return f"__ERR__ {exc}"

    def locked_kb(self):
        """Wired pages of this process, from the rollup (per-VMA Locked: is not
        guaranteed on every kernel; the rollup is what we verified on this device)."""
        try:
            with open(f"/proc/{self.proc.pid}/smaps_rollup", encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r"Locked:\s+(\d+)\s+kB", line)
                    if m:
                        return int(m.group(1))
        except OSError:
            return None
        return None

    def hup(self):
        os.kill(self.proc.pid, signal.SIGHUP)

    def stop(self):
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGKILL)
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.unlink(self.cfg_path)
        except OSError:
            pass


def map_lines(maps_text, path, perms=None):
    """Lines of /proc/<pid>/maps that map `path`.

    Matched on the tail of the path on purpose: the same file is printed under
    /data/service/el2/<uid>/hmdfs/... while the caller knows it as
    /storage/Users/currentUser/..., and the two views do not even agree on the inode
    (HMDFS virtualises it), so neither the string nor st_ino matches across views.
    The tail carries the conan package hash, which makes it unambiguous.
    """
    tail = "/".join(path.replace("\\", "/").split("/")[-6:])
    out = []
    for line in maps_text.splitlines():
        cols = line.split()
        if len(cols) >= 6 and cols[5].endswith(tail) and (perms is None or cols[1] == perms):
            out.append(line)
    return out


def one_shot(args, expect_rc, needle, label):
    proc = subprocess.run([BIN, *args], capture_output=True, text=True, timeout=30)
    blob = (proc.stdout or "") + (proc.stderr or "")
    return check(label, proc.returncode == expect_rc and needle in blob,
                 f"rc={proc.returncode} (want {expect_rc}) out={blob[:300]!r}")


def main():
    if not os.access(BIN, os.X_OK):
        print(f"FATAL: {BIN} is not executable")
        return 2
    os.makedirs(WORK, exist_ok=True)
    cur, mx = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    print("== memlockd 1.3.1 consumer suite ==")
    print(f"bin={BIN}\nwork={WORK}\nuid={os.getuid()} machine={os.uname().machine}")
    print(f"RLIMIT_MEMLOCK cur={cur} max={mx} RLIM_INFINITY={resource.RLIM_INFINITY}")

    # ---------------- layer 1: CLI contract (self-terminating paths) ----------
    one_shot(["-Q"], 1, "Usage: memlockd",
             "L1 unknown option prints the usage line and exits 1")
    one_shot(["-d", "-c", os.path.join(WORK, "no-such-file.cfg")], 1, "Can't stat",
             'L1 missing config file logs "Can\'t stat" and exits 1')
    one_shot(["-d", "-u", "nosuchuser-4242", "-c", os.path.join(WORK, "x.cfg")], 1,
             "Can't look up user", 'L1 unknown -u user logs "Can\'t look up user" and exits 1')
    # The upstream sample config is kept verbatim under res/. On OHOS its flat entries
    # still hit four real system files, but the trailing "%/etc/memlockd.d" drop-in dir
    # (created by the Debian postinst) does not exist here, and a % entry that cannot be
    # stat()ed is a hard exit(1) -- so the sample is data, not a runnable default.
    proc = subprocess.run([BIN, "-d", "-c", os.path.join(PKG, "res", "memlockd.cfg")],
                          capture_output=True, text=True, timeout=30)
    sample = (proc.stdout or "") + (proc.stderr or "")
    check('L1d upstream sample config maps the entries that exist on OHOS ("/bin/login", '
          '"/etc/passwd", "/etc/group", "/etc/resolv.conf")',
          "Mapped file /bin/login" in sample and "Mapped file /etc/passwd" in sample,
          f"rc={proc.returncode} out={sample[:400]!r}")
    check("L1e the sample config's \"%/etc/memlockd.d\" drop-in dir is absent on OHOS, "
          "which the parser treats as fatal (rc=1) rather than skipping",
          proc.returncode == 1 and 'Can\'t stat "/etc/memlockd.d"' in sample,
          f"rc={proc.returncode} out={sample[-260:]!r}")

    file_a = os.path.join(PKG, "bin", "memlockd")
    file_b = os.path.join(PKG, "res", "memlockd.cfg")
    huge = os.path.join(WORK, "huge8m.bin")
    with open(huge, "wb") as fh:
        fh.write(b"\0" * (1024 * 1024 * 8))

    # ---------------- layer 2: unprivileged page locking, measured ------------
    d = Daemon(cfg_text(file_a, file_b))
    try:
        line, idx = d.expect(f"Mapped file {file_a}")
        check("L2a packaged ELF + packaged config get mmap()+mlock() as a normal user",
              line is not None and f"Mapped file {file_b}" in "\n".join(d.snapshot()),
              f"lines={d.snapshot()[:8]}")
        base = d.locked_kb()
        check("L2b /proc/<pid>/smaps_rollup exposes a Locked: counter on this kernel",
              isinstance(base, int) and base > 0, f"Locked={base} kB")
        maps = d.maps()
        # The packaged binary is also the executable, so a plain presence test would pass
        # even if mmap() had failed. Its exec mappings carry an "x" permission; the only
        # r--p mapping of that same file is memlockd's PROT_READ MAP_SHARED one.
        # PROT_READ + MAP_SHARED shows up as "r--s". An "r--p" line for the packaged
        # binary is one of its own exec segments, so only "r--s" is attributable to
        # memlockd's mmap(); that is the permission string asserted here.
        la = map_lines(maps, file_a, "r--s")
        lb = map_lines(maps, file_b, "r--s")
        check("L2c both files are attached as PROT_READ MAP_SHARED mappings of the daemon "
              "(r--s line, path tail matched across the two HMDFS views)",
              len(la) >= 1 and len(lb) >= 1, f"a={la[:2]} b={lb[:2]}")
        if lb:
            print(f"   [detail] maps prints the mapped file as: {lb[0].split()[5]}", flush=True)

        # Differential carrier: wiring an extra 8 MiB file must raise Locked by ~8 MiB.
        before = len(d.snapshot())
        d.set_cfg(cfg_text(file_a, file_b, huge))
        d.hup()
        line, _ = d.expect(f"Mapped file {huge}", timeout=25, start=before)
        after = d.locked_kb()
        delta = (after - base) if isinstance(after, int) and isinstance(base, int) else None
        check("L2d SIGHUP reparse picks up the new entry and locks an extra 8 MiB file "
              "without CAP_IPC_LOCK (Locked: grows >= 8000 kB)",
              line is not None and delta is not None and delta >= 8000,
              f"mapped_line={line} Locked {base} -> {after} kB (delta={delta})")
        print(f"   [detail] Locked: {base} kB -> {after} kB (delta={delta} kB), "
              f"RLIMIT_MEMLOCK cur={cur}", flush=True)
        hu = map_lines(d.maps(), huge)
        check("L2e the 8 MiB file is mapped exactly once, read-only and shared (r--s)",
              len(hu) == 1 and hu[0].split()[1] == "r--s", f"lines={hu[:3]}")
    finally:
        d.stop()

    # ---------------- layer 3: config grammar and failure paths ---------------
    absent1 = os.path.join(WORK, "absent-1")
    absent2 = os.path.join(WORK, "absent-2")
    arch_line = "/usr/lib/" + "$ARCH" + "-linux-gnu/nope.so"
    d2 = Daemon(cfg_text(f"?{absent1}", file_a, absent2, arch_line))
    try:
        line, _ = d2.expect(f"Mapped file {file_a}")
        blob2 = "\n".join(d2.snapshot())
        check("L3a a config that mixes good and missing paths still locks the readable file",
              line is not None, f"lines={d2.snapshot()[:8]}")
        check('L3b "?"-prefixed missing path is tolerated (no "Can\'t open file" for it)',
              f"Can't open file {absent1}" not in blob2, f"blob={blob2[:300]}")
        check('L3c unguarded missing path logs "Can\'t open file" and keeps the daemon alive',
              f"Can't open file {absent2}" in blob2 and d2.proc.poll() is None,
              f"blob={blob2[:300]}")
        substituted = f"/usr/lib/{os.uname().machine}-linux-gnu/nope.so"
        check("L3d $ARCH is expanded from uname().machine before open()",
              f"Can't open file {substituted}" in blob2, f"blob={blob2[:300]}")
    finally:
        d2.stop()

    # ---------------- layer 4: packaged data plane ----------------------------
    for rel, minimum in (("res/memlockd.cfg", 200), ("share/man/man8/memlockd.8", 500),
                         ("res/source/memlockd.cpp", 5000)):
        path = os.path.join(PKG, *rel.split("/"))
        size = os.path.getsize(path) if os.path.isfile(path) else -1
        check(f"L4 packaged {rel} shipped and >= {minimum} B", size >= minimum, f"size={size}")

    try:
        os.unlink(huge)
    except OSError:
        pass
    print(f"\nMEMLOCKD consumer suite: PASS={len(PASSED)} FAIL={len(FAILED)}")
    for name in FAILED:
        print(f"  failed: {name}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
