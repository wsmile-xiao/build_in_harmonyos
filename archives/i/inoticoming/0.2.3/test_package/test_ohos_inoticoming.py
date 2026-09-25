#!/usr/bin/env python3
"""HarmonyOS-specific test for the packaged inoticoming (OHOS 专项测试).

Usage: test_ohos_inoticoming.py <inoticoming-binary> <workdir>

This is an OHOS-only addition (upstream has no test suite at all, see
test_package/MANIFEST.yml).  It asserts the HarmonyOS platform contracts
the daemon actually depends on, which a plain --version/--help smoke check
would not cover:

  1. OHOS target identity — the packaged ELF must be an AArch64 ELF64 PIE
     whose PT_INTERP is the HarmonyOS musl loader
     (/lib/ld-musl-aarch64.so.1).  This proves the artifact is a real
     OHOS build and gives test_package something to run on the target.
  2. inotify kernel ABI — IN_CLOSE_WRITE and IN_MOVED_TO must be delivered
     by the OHOS kernel to the daemon and dispatch the configured action
     (inoticoming is useless if the platform lacks the inotify syscalls).

This script is OHOS-only: it is launched by test_package/conanfile.py only
when the test target is OHOS (on other targets it is reported as skipped,
because case 1 asserts the OHOS musl loader path).  3. --initialsearch on the OHOS filesystem — files that already exist in
     the watched directory must be processed, i.e. readdir() must report
     them with d_type == DT_REG on HarmonyOS (DT_UNKNOWN would silently
     skip every pre-existing file).
  4. --pid-file — the pid file must contain the daemon's real pid
     (getpid/printf("%llu") on OHOS libc, and the readiness handshake).
  5. --chdir — the action must run with cwd set to the watched directory
     (fork/chdir/execvp chain on OHOS libc).
  6. daemonization + --logfile — the production mode (no --foreground) must
     detach, keep running and log the dispatched action into --logfile on
     an OHOS system without syslogd; the process is then stopped through
     the pid file and must exit 0.

Every case runs in its own freshly created directory (never a reused one)
and prints PASS/FAIL; the run ends with a machine readable
"RESULT: N passed, M failed" line (parsed by test_package/conanfile.py).
"""

import os
import shutil
import signal
import struct
import subprocess
import sys
import time

PASS = 0
FAIL = 0

PT_INTERP = 3
ET_DYN = 3
EM_AARCH64 = 0xB7
OHOS_MUSL_LOADER = "/lib/ld-musl-aarch64.so.1"

ACTION_TEMPLATE = """#!/bin/sh
# inoticoming OHOS-test action: $1 = marker file, $2 = matched filename
printf '%s|%s\\n' "$PWD" "$2" >> "$1"
"""


def ok(message):
    global PASS
    PASS += 1
    print("PASS: %s" % message)


def bad(message):
    global FAIL
    FAIL += 1
    print("FAIL: %s" % message)


def fresh_dir(base, name):
    """Create an empty directory, removing leftovers from earlier runs."""
    path = os.path.join(base, name)
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    return path


def elf_details(path):
    """Minimal ELF reader: class/endianness/machine/type plus PT_INTERP."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    ei_class, ei_data = data[4], data[5]
    endian = "<" if ei_data == 1 else ">"
    e_type = struct.unpack(endian + "H", data[16:18])[0]
    e_machine = struct.unpack(endian + "H", data[18:20])[0]
    e_phoff = struct.unpack(endian + "Q", data[32:40])[0]
    e_phentsize = struct.unpack(endian + "H", data[54:56])[0]
    e_phnum = struct.unpack(endian + "H", data[56:58])[0]
    interp = None
    for index in range(e_phnum):
        off = e_phoff + index * e_phentsize
        p_type = struct.unpack(endian + "I", data[off:off + 4])[0]
        if p_type == PT_INTERP:
            p_offset = struct.unpack(endian + "Q", data[off + 8:off + 16])[0]
            p_filesz = struct.unpack(endian + "Q", data[off + 32:off + 40])[0]
            interp = data[p_offset:p_offset + p_filesz].split(b"\0")[0].decode(
                "utf-8", "replace"
            )
    return {
        "ei_class": ei_class,
        "ei_data": ei_data,
        "e_type": e_type,
        "e_machine": e_machine,
        "interp": interp,
    }


def find_shell():
    for candidate in ("/bin/sh", "/usr/bin/sh", "/system/bin/sh"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def write_action(path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(ACTION_TEMPLATE)
    os.chmod(path, 0o755)
    return path


def wait_for(predicate, timeout=15.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def read_entries(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return [line.strip() for line in handle if line.strip()]


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def names_in(marker):
    return sorted({entry.split("|")[-1] for entry in read_entries(marker)})


def start_foreground(binary, case_dir, extra_args, log_name="daemon.log"):
    """Start `inoticoming --foreground --pid-file …`, wait for its own pid."""
    log = open(os.path.join(case_dir, log_name), "wb")
    pid_path = os.path.join(case_dir, "daemon.pid")
    args = [binary, "--foreground", "--pid-file", pid_path] + extra_args
    proc = subprocess.Popen(
        args, cwd=case_dir, stdout=log, stderr=subprocess.STDOUT
    )

    def pid_matches():
        if not os.path.isfile(pid_path):
            return False
        return read_text(pid_path).strip() == str(proc.pid)

    ready = wait_for(pid_matches, timeout=20)
    return proc, log, ready


def stop_foreground(proc, log):
    if proc.poll() is None:
        # inoticoming installs its SIGTERM handler right after writing the pid
        # file, so give the daemon a moment before signalling.
        time.sleep(0.5)
        proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    log.close()
    return proc.returncode


def case_ohos_target_identity(binary):
    try:
        info = elf_details(binary)
    except Exception as exc:
        bad("OHOS target identity: cannot parse ELF (%s)" % exc)
        return
    problems = []
    if info["ei_class"] != 2:
        problems.append("not ELF64 (ei_class=%s)" % info["ei_class"])
    if info["ei_data"] != 1:
        problems.append("not little-endian (ei_data=%s)" % info["ei_data"])
    if info["e_machine"] != EM_AARCH64:
        problems.append("e_machine=0x%x (expected AArch64 0x%x)"
                        % (info["e_machine"], EM_AARCH64))
    if info["e_type"] != ET_DYN:
        problems.append("e_type=%s (expected PIE/ET_DYN %s)"
                        % (info["e_type"], ET_DYN))
    if info["interp"] != OHOS_MUSL_LOADER:
        problems.append("PT_INTERP=%r (expected %r)"
                        % (info["interp"], OHOS_MUSL_LOADER))
    if problems:
        bad("OHOS target identity: " + "; ".join(problems))
    else:
        ok("OHOS target identity: ELF64 AArch64 PIE, PT_INTERP=%s"
           % info["interp"])


def case_inotify_kernel_abi(binary, shell, workdir):
    case = fresh_dir(workdir, "inotify-abi")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    action = write_action(os.path.join(case, "action.sh"))
    proc, log, ready = start_foreground(
        binary, case, [watch, shell, action, marker, "{}", ";"]
    )
    try:
        if not ready:
            bad("inotify kernel ABI: daemon never became ready")
            return
        with open(os.path.join(watch, "ohos-write.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("payload\n")
        staging = os.path.join(case, "ohos-rename.txt.part")
        with open(staging, "w", encoding="utf-8") as handle:
            handle.write("payload\n")
        os.rename(staging, os.path.join(watch, "ohos-rename.txt"))
        delivered = wait_for(
            lambda: names_in(marker) == ["ohos-rename.txt", "ohos-write.txt"],
            timeout=20,
        )
        if delivered:
            ok("inotify kernel ABI: IN_CLOSE_WRITE and IN_MOVED_TO delivered "
               "on OHOS")
        else:
            bad("inotify kernel ABI: events missing (marker=%r)"
                % read_entries(marker))
    finally:
        stop_foreground(proc, log)


def case_initialsearch_dtype(binary, shell, workdir):
    case = fresh_dir(workdir, "initialsearch")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    action = write_action(os.path.join(case, "action.sh"))
    # Pre-existing regular files: --initialsearch must pick them up, which
    # requires readdir()/d_type == DT_REG on this filesystem.
    for name in ("already-1.pkg", "already-2.pkg"):
        with open(os.path.join(watch, name), "w", encoding="utf-8") as handle:
            handle.write("payload\n")
    proc, log, ready = start_foreground(
        binary, case, ["--initialsearch", watch, shell, action, marker, "{}", ";"]
    )
    try:
        if not ready:
            bad("--initialsearch: daemon never became ready")
            return
        found = wait_for(
            lambda: names_in(marker) == ["already-1.pkg", "already-2.pkg"],
            timeout=20,
        )
        if found:
            ok("--initialsearch processed pre-existing files "
               "(readdir d_type == DT_REG on OHOS)")
        else:
            bad("--initialsearch missed pre-existing files (marker=%r) — "
                "readdir d_type may be DT_UNKNOWN on this OHOS filesystem"
                % read_entries(marker))
    finally:
        stop_foreground(proc, log)


def case_chdir_and_pidfile(binary, shell, workdir):
    case = fresh_dir(workdir, "chdir-pidfile")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    action = write_action(os.path.join(case, "action.sh"))
    proc, log, ready = start_foreground(
        binary, case,
        [watch, "--chdir", watch, shell, action, marker, "{}", ";"],
    )
    try:
        if not ready:
            bad("--chdir/--pid-file: daemon never became ready")
            return
        recorded = read_text(os.path.join(case, "daemon.pid")).strip()
        if recorded == str(proc.pid):
            ok("--pid-file contains the real daemon pid (%s) on OHOS" % recorded)
        else:
            bad("--pid-file content %r != spawned pid %s" % (recorded, proc.pid))

        with open(os.path.join(watch, "ohos-cwd.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("payload\n")
        if not wait_for(lambda: read_entries(marker), timeout=20):
            bad("--chdir: action never ran")
            return
        entry = read_entries(marker)[-1]
        cwd, _, name = entry.partition("|")
        if os.path.realpath(cwd) == os.path.realpath(watch) and name == "ohos-cwd.txt":
            ok("--chdir action ran inside the watched directory with the right name")
        else:
            bad("--chdir action cwd/name mismatch: %r (expected %r|ohos-cwd.txt)"
                % (entry, watch))
    finally:
        stop_foreground(proc, log)


def case_daemonize_logfile(binary, shell, workdir):
    case = fresh_dir(workdir, "daemonize")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    pidfile = os.path.join(case, "daemon.pid")
    logfile = os.path.join(case, "logfile")
    action = write_action(os.path.join(case, "action.sh"))
    # Production mode: no --foreground, so the daemon()s itself and logs
    # through --logfile instead of syslog (OHOS ships no syslogd).
    proc = subprocess.run(
        [binary, "--pid-file", pidfile, "--logfile", logfile, watch,
         shell, action, marker, "{}", ";"],
        cwd=case, capture_output=True, text=True, timeout=60,
    )
    daemon_pid = None
    try:
        # The pid file is created (empty) before daemon() and filled in
        # afterwards by the detached child, so wait for its *content*.
        def pid_written():
            text = read_text(pidfile).strip()
            return text.isdigit() and int(text) > 0

        if not wait_for(pid_written, timeout=20):
            bad("daemonize/--logfile: parent rc=%s and no pid in pid file (%r)"
                % (proc.returncode, read_text(pidfile)[:60]))
            return
        daemon_pid = int(read_text(pidfile).strip())
        with open(os.path.join(watch, "ohos-daemon.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("payload\n")
        if wait_for(lambda: "ohos-daemon.txt" in read_text(logfile), timeout=20):
            ok("daemonized mode logged the dispatched action into --logfile "
               "(no syslogd needed on OHOS)")
        else:
            bad("daemonize/--logfile: action log missing (logfile=%r marker=%r)"
                % (read_text(logfile)[-300:], read_entries(marker)))
    finally:
        if daemon_pid:
            try:
                os.kill(daemon_pid, signal.SIGTERM)
            except OSError:
                pass
            for _ in range(50):
                try:
                    os.kill(daemon_pid, 0)
                except OSError:
                    break
                time.sleep(0.1)


def main():
    if len(sys.argv) != 3:
        print("usage: test_ohos_inoticoming.py <inoticoming-binary> <workdir>")
        return 2
    binary = sys.argv[1]
    workdir = sys.argv[2]
    if not os.path.isfile(binary):
        print("FAIL: inoticoming binary not found: %s" % binary)
        return 1
    shell = find_shell()
    if shell is None:
        print("FAIL: no POSIX shell found for the test action")
        return 1
    os.makedirs(workdir, exist_ok=True)
    print("[ohos-test] binary: %s" % binary)
    print("[ohos-test] shell : %s" % shell)
    print("[ohos-test] tmpdir: %s" % workdir)

    case_ohos_target_identity(binary)
    case_inotify_kernel_abi(binary, shell, workdir)
    case_initialsearch_dtype(binary, shell, workdir)
    case_chdir_and_pidfile(binary, shell, workdir)
    case_daemonize_logfile(binary, shell, workdir)

    print("RESULT: %d passed, %d failed" % (PASS, FAIL))
    if FAIL:
        print("test_ohos_inoticoming.py FAILED")
        return 1
    print("test_ohos_inoticoming.py PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
