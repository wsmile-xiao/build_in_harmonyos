#!/usr/bin/env python3
"""pty-driven functional test for pconsole 1.2.0 (HarmonyOS PC / OpenHarmony aarch64).

pconsole is an interactive tty-multiplexer: it refuses to start unless it runs
with an effective uid of 0 *and* stdin is a terminal, and all of its behaviour
lives in a command loop that reads from that terminal.  A plain
``subprocess.run([...], capture_output=True)`` can therefore only ever observe
the two guard messages — so every functional case here is driven through a real
pseudo-terminal.

Cases
-----
F1  banner + command-mode prompt            pconsole starts under a pty
F2  `version`                               prints "pconsole 1.2.0 WJ101"
F3  `help`                                  prints the whole command table
F4  `help warranty`                         prints the GPL warranty text
F5  `list`                                  "currently not attached to any terminal device"
F6  unknown verb                            "unknown command 'nosuchverb'"
F7  `attach` without argument               usage line
F8  `attach /no/such/tty`                   ENOENT reported, no crash
F9  `echo on|off`                           echo state toggles and is reported
F10 `connect` with nothing attached         "currently not attached to any terminal device"

M1  core feature: pconsole <tty> attaches the device, `list` shows it, and a
    keystroke typed at pconsole is injected into the attached terminal through
    ioctl(TIOCSTI).  TIOCSTI is a privileged legacy ioctl that some kernels
    refuse outright, so the harness probes it first and asserts the matching
    branch: delivery when the ioctl works, clean detach + ioctl error when it
    does not.

M1b the privilege-drop tail of that same injection must not fail.  Note the
    injected byte is delivered by ioctl(TIOCSTI) *before* the trailing
    seteuid() runs, so a build that dies there still looks successful to M1 --
    which is why the boundary itself is enforced in H5 rather than inferred
    from the exit status here.

H1  ELF64 / EM_AARCH64                     target architecture of the artifact
H2  DT_NEEDED == libc.so only              R26: no same-named system library
H3  no SIGSYS on the privilege-drop path    OpenHarmony seccomp boundary (E051)
H4  non-tty invocation is refused           the isatty() guard still holds
H5  no privileged-id syscall on the         the boundary, actually enforced:
    keystroke-injection path                the child arms a seccomp-bpf filter
                                             that traps the whole set*-id family
                                             before exec, reproducing the
                                             HarmonyOS uncatchable SIGSYS.  A
                                             build that emits one of those
                                             syscalls on the injection path dies
                                             and this case fails; a fully
                                             guarded build issues none and
                                             survives.  This is what pins down
                                             the third seteuid() call site --
                                             the "drop root privs again" tail of
                                             put_conn(), which every injected
                                             keystroke traverses.  Reported as
                                             `skip:` (never as a pass) on a host
                                             whose kernel/container refuses the
                                             filter.

Usage: pconsole_pty_test.py <bindir>
Exit code 0 = every case passed, non-zero = failure.
"""
import ctypes
import ctypes.util
import json
import os
import pty
import select
import struct
import subprocess
import sys
import time

TIOCSTI = 0x5412
ROOT_GATE_MSG = "You must be root to run this program or this program should be setuid root."
NOT_A_TTY_MSG = "pconsole: not a tty"

PASSED = []
FAILED = []
SKIPPED = []


def record(name, ok, detail=""):
    if ok:
        PASSED.append(name)
        print("ok: %s%s" % (name, (" (%s)" % detail) if detail else ""))
    else:
        FAILED.append(name)
        print("FAIL: %s%s" % (name, (" (%s)" % detail) if detail else ""))
    sys.stdout.flush()


def skip(name, reason):
    """Record a check that could not be executed.

    Deliberately *not* counted as a pass: a check that cannot run must never
    inflate the pass total, or the declared-vs-executed assertion counts stop
    meaning anything.
    """
    SKIPPED.append(name)
    print("skip: %s (%s)" % (name, reason))
    sys.stdout.flush()


# ── ELF inspection (pure Python: no readelf/llvm-nm needed on the worker) ─────

def elf_facts(path):
    """Return (e_machine, is_64bit, little_endian, needed, interp)."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"\x7fELF", "not an ELF file"
    ei_class, ei_data = data[4], data[5]
    is_64 = ei_class == 2
    end = "<" if ei_data == 1 else ">"
    if is_64:
        e_machine = struct.unpack_from(end + "H", data, 18)[0]
    else:
        e_machine = struct.unpack_from(end + "H", data, 18)[0]
    # program headers -> PT_INTERP (3)
    if is_64:
        e_phoff, = struct.unpack_from(end + "Q", data, 32)
        e_phentsize, e_phnum = struct.unpack_from(end + "HH", data, 54)
    else:
        e_phoff, = struct.unpack_from(end + "I", data, 28)
        e_phentsize, e_phnum = struct.unpack_from(end + "HH", data, 42)
    interp = ""
    loads = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if is_64:
            p_type, = struct.unpack_from(end + "I", data, off)
            p_offset, = struct.unpack_from(end + "Q", data, off + 8)
            p_filesz, = struct.unpack_from(end + "Q", data, off + 32)
        else:
            p_type, = struct.unpack_from(end + "I", data, off)
            p_offset, = struct.unpack_from(end + "I", data, off + 4)
            p_filesz, = struct.unpack_from(end + "I", data, off + 16)
        loads.append((p_type, p_offset, p_filesz))
        if p_type == 3:
            raw = data[p_offset:p_offset + p_filesz]
            interp = raw.split(b"\x00", 1)[0].decode("ascii", "replace")
    needed = []
    for p_type, p_offset, p_filesz in loads:
        if p_type != 2:  # PT_DYNAMIC
            continue
        strtab_off = None
        dyn_entsz = 16 if is_64 else 8
        n = p_filesz // dyn_entsz
        raw_needed = []
        for i in range(n):
            off = p_offset + i * dyn_entsz
            tag, val = struct.unpack_from(end + ("qQ" if is_64 else "iI"), data, off)
            if tag == 5 and strtab_off is None:
                strtab_off = val
            if tag == 1:
                raw_needed.append(val)
        if strtab_off is not None:
            for v in raw_needed:
                end_s = data.index(b"\x00", strtab_off + v)
                needed.append(data[strtab_off + v:end_s].decode("ascii", "replace"))
    return e_machine, is_64, end == "<", needed, interp


def check_elf(binpath):
    try:
        e_machine, is_64, little, needed, interp = elf_facts(binpath)
    except Exception as exc:  # noqa: BLE001 - report, do not mask
        record("H1_elf64_aarch64", False, "cannot parse ELF: %s" % exc)
        record("H2_libc_only_needed", False, "cannot parse ELF")
        return
    record("H1_elf64_aarch64", is_64 and little and e_machine == 183,
           "class=%s endian=%s e_machine=%d" % ("ELF64" if is_64 else "ELF32",
                                               "little" if little else "big",
                                               e_machine))
    # R26: never ship/link a library that shares its name with a system library.
    offenders = [n for n in needed if n not in ("libc.so", "libc.so.6", "libc.musl-aarch64.so.1")]
    record("H2_libc_only_needed", not offenders,
           "DT_NEEDED=%s interp=%s" % (needed, interp or "<none>"))


# ── pty plumbing ─────────────────────────────────────────────────────────────

def run_pty(argv, script, settle=0.45, tail=1.2, env=None, pre_exec=None,
            hook_err=None):
    """Run argv under a pty, feed `script` (list of byte strings), return (rc, out).

    On OpenHarmony reading the pty master after the child exits raises EIO
    instead of returning EOF, so the read loop treats OSError as end-of-output
    and then reaps the child for its real exit status.

    `pre_exec`, when given, is called in the child between fork() and exec().
    That is the only place a seccomp filter can be installed such that it is
    inherited by the exec'd image and cannot be undone by it.  If it raises,
    the child reports the reason on `hook_err` (a writable fd) and exits 126
    instead of exec'ing, so the caller can tell "could not arm the check"
    apart from "the check fired".
    """
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    pid, fd = pty.fork()
    if pid == 0:
        try:
            if pre_exec is not None:
                pre_exec()
            if env:
                os.execve(argv[0], argv, full_env)
            else:
                os.execv(argv[0], argv)
        except BaseException as exc:  # noqa: BLE001 - child must not unwind
            if hook_err is not None:
                try:
                    os.write(hook_err, ("%s: %s" % (type(exc).__name__, exc)).encode())
                except Exception:  # noqa: BLE001
                    pass
            os._exit(126)
        os._exit(127)

    out = b""

    def pump(seconds):
        nonlocal out
        stop = time.time() + seconds
        while time.time() < stop:
            r, _, _ = select.select([fd], [], [], 0.05)
            if not r:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                return False
            if not chunk:
                return False
            out += chunk
        return True

    time.sleep(settle)
    pump(0.3)
    for item in script:
        try:
            os.write(fd, item)
        except OSError:
            break
        if not pump(0.35):
            break
    pump(tail)

    rc = None
    stop = time.time() + 3.0
    while time.time() < stop:
        try:
            wpid, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            break
        if wpid:
            rc = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
            break
        pump(0.1)
    if rc is None:
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        rc = -1
    try:
        os.close(fd)
    except OSError:
        pass
    return rc, out.decode("utf-8", "replace")


def run_plain(argv):
    """Run argv with all three standard streams pointed at /dev/null.

    Returns (rc, combined output).  Used for the non-tty guard case, where the
    point is precisely that stdin is *not* a terminal.
    """
    devnull = os.open(os.devnull, os.O_RDWR)
    pid = os.fork()
    if pid == 0:
        try:
            os.dup2(devnull, 0)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.execv(argv[0], argv)
        except Exception:  # noqa: BLE001
            pass
        os._exit(127)
    _, status = os.waitpid(pid, 0)
    os.close(devnull)
    rc = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
    try:
        p = subprocess.run([argv[0]], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        combined = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        combined = "<timeout>"
    return rc, combined


def main():
    if len(sys.argv) < 2:
        print("usage: pconsole_pty_test.py <bindir>")
        return 2
    bindir = sys.argv[1]
    binpath = os.path.join(bindir, "pconsole")
    if not (os.path.isfile(binpath) and os.access(binpath, os.X_OK)):
        print("ABORT: %s missing or not executable" % binpath)
        print("PCONSOLE_PTY_RESULT={\"executed\": false, \"passed\": false}")
        return 1
    print("harness: driving %s" % binpath)

    check_elf(binpath)

    # H4: with stdin not a tty the binary must refuse, and it must refuse with
    # the guard message rather than being killed by the kernel.
    rc, combined = run_plain([binpath])
    combined = combined.strip()
    record("H4_non_tty_invocation_refused",
           rc != 0 and (ROOT_GATE_MSG in combined or NOT_A_TTY_MSG in combined)
           and rc not in (159, -31),
           "rc=%s out=%r" % (rc, combined[:90]))

    # H3: the same guard path must not be killed by the uncatchable SIGSYS that
    # the unguarded seteuid() calls trigger on OpenHarmony/HarmonyOS.
    # NOTE: run_plain reports a fatal signal as a *negative* number, so the
    # check must compare against -31.  Comparing against 159 (the exit status
    # a shell reports) could never fire here and made this case vacuous.
    record("H3_no_sigsys_on_startup",
           rc not in (159, -31) and "Bad system call" not in combined,
           "rc=%s (159 or -31 == SIGSYS)" % rc)

    if os.geteuid() != 0:
        record("F1_root_gate_enforced", ROOT_GATE_MSG in combined,
               "euid=%d -> pconsole requires root, functional pty cases skipped"
               % os.geteuid())
        print("PCONSOLE_PTY_RESULT=%s" % _summary())
        return 0 if not FAILED else 1

    # F1 + F2: banner, command mode, version
    rc, out = run_pty([binpath], [b"version\r", b"exit\r"])
    record("F1_banner_and_command_mode",
           "pconsole WJ101" in out and "pconsole command mode" in out and rc == 0,
           "rc=%s" % rc)
    record("F2_version_command",
           "pconsole 1.2.0 WJ101" in out and "Copyright (C) 2001" in out,
           "version banner")

    # F3 + F4: help table and help warranty
    rc, out = run_pty([binpath], [b"help\r", b"help warranty\r", b"exit\r"])
    record("F3_help_command_table",
           all(word in out for word in ("attach", "detach", "list", "connect", "quit", "exit"))
           and "Give help about the available commands" in out,
           "rc=%s" % rc)
    record("F4_help_warranty", "GNU General Public License" in out and
           "WITHOUT ANY WARRANTY" in out, "warranty text")

    # F5 + F6: list with no connections, unknown verb
    rc, out = run_pty([binpath], [b"list\r", b"nosuchverb\r", b"exit\r"])
    record("F5_list_without_connections",
           "pconsole: currently not attached to any terminal device" in out, "rc=%s" % rc)
    record("F6_unknown_command", "pconsole: unknown command 'nosuchverb'" in out, "rc=%s" % rc)

    # F7 + F8: attach argument validation and ENOENT
    rc, out = run_pty([binpath], [b"attach\r", b"attach /no/such/tty\r", b"exit\r"])
    record("F7_attach_requires_argument",
           "usage: attach [hostname#]<tty device name> [...]" in out, "rc=%s" % rc)
    record("F8_attach_missing_device_reports_errno",
           "attaching /no/such/tty" in out and "No such file or directory" in out, "rc=%s" % rc)

    # F9: echo toggle
    rc, out = run_pty([binpath], [b"echo off\r", b"echo on\r", b"echo bogus\r", b"exit\r"])
    record("F9_echo_toggle",
           "echo is now toggled off" in out and "echo is now toggled on" in out
           and "usage: echo [on|off]" in out, "rc=%s" % rc)

    # F10: connect with nothing attached
    rc, out = run_pty([binpath], [b"connect\r", b"exit\r"])
    record("F10_connect_without_connections",
           "pconsole: currently not attached to any terminal device" in out, "rc=%s" % rc)

    # M1: the actual multiplexing feature — attach a real pty and type into it.
    _case_multiplex(binpath)

    # H5: same injection path, but with the E051 privileged-syscall boundary
    # actually enforced, so an unguarded seteuid() cannot hide behind a
    # successful-looking exit status.
    _case_no_setid_syscall(binpath)

    print("PCONSOLE_PTY_RESULT=%s" % _summary())
    return 0 if not FAILED else 1


def _tiocsti_available():
    """Probe ioctl(TIOCSTI) on a throwaway pty; return (ok, detail).

    TIOCSTI is a privileged legacy ioctl that some kernels refuse outright, so
    the capability has to be measured instead of assumed.  A throwaway pty is
    used so the probe leaves no trace in the pty under test.
    """
    try:
        probe_master, probe_slave = pty.openpty()
    except OSError as exc:
        return False, "no-pty-for-probe: %s" % exc
    try:
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
        except OSError as exc:
            return False, "no-libc: %s" % exc
        buf = ctypes.c_char(b"\x01")
        ctypes.set_errno(0)
        rc = libc.ioctl(probe_slave, TIOCSTI, ctypes.byref(buf))
        if rc == 0:
            return True, "ioctl(TIOCSTI) accepted"
        return False, os.strerror(ctypes.get_errno())
    finally:
        for fd in (probe_master, probe_slave):
            try:
                os.close(fd)
            except OSError:
                pass


def _case_multiplex(binpath):
    tiocsti_ok, tiocsti_detail = _tiocsti_available()
    print("info: TIOCSTI probe -> %s (%s)" % (tiocsti_ok, tiocsti_detail))
    try:
        master, slave = pty.openpty()
    except OSError as exc:
        record("M1_keystroke_multiplexing", False, "no pty available: %s" % exc)
        return
    slave_name = os.ttyname(slave)

    # pconsole <tty> attaches at startup and then stays in its raw multiplexing
    # loop, so a plain byte typed at pconsole is injected into the target
    # terminal and echoed back out of the pty master by the target's line
    # discipline.  Ctrl-A enters command mode, where `list` reports the attached
    # device and `exit` detaches.
    # NOTE: Ctrl-A alone does *not* leave command mode — only `connect`/`exit` do
    # (command_mode() re-prompts while FLAGS_CMD_MODE is still set).
    # "Z" is used as the probe byte: the target only ever receives pconsole's
    # own banner text plus what we inject, and that banner has no capital Z.
    probe_byte = b"Z"
    script = [probe_byte, b"\x01", b"list\r", b"exit\r"]
    rc, out = run_pty([binpath, slave_name], script, settle=0.6, tail=1.5)

    delivered = b""
    try:
        os.set_blocking(master, False)
        time.sleep(0.2)
        while True:
            chunk = os.read(master, 4096)
            if not chunk:
                break
            delivered += chunk
    except (BlockingIOError, OSError):
        pass

    still_attached = "Currently attached to:" in out
    attached = slave_name in out
    banner = b"[pconsole attached from tty" in delivered
    if tiocsti_ok:
        ok = attached and still_attached and banner and rc == 0 and probe_byte in delivered
        detail = ("attached=%s list_shows_device=%s banner_to_target=%s rc=%s "
                  "injected_byte_in_target=%s"
                  % (attached, still_attached, banner, rc, probe_byte in delivered))
    else:
        ok = attached and rc == 0 and "ioctl()" in out
        detail = ("TIOCSTI unavailable (%s): attached=%s rc=%s ioctl_error_reported=%s"
                  % (tiocsti_detail, attached, rc, "ioctl()" in out))
    record("M1_keystroke_multiplexing", ok, detail)
    # The guard under test: reaching this point at all means put_conn()'s
    # seteuid() calls did not kill the process.  Assert on the negative signal
    # convention used by run_pty (-31) as well as the shell-style 159, and on
    # the privilege-drop error text, so this case can actually fail.
    record("M1b_no_sigsys_on_privilege_regain",
           rc not in (159, -31) and "Bad system call" not in out
           and "failed to drop root privs" not in out,
           "rc=%s (159 or -31 == SIGSYS); guarded seteuid() must not fail" % rc)

    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass


# ── E051 boundary emulation: seccomp-bpf trap on the privileged id syscalls ──
#
# HarmonyOS kills a process that issues setuid/setreuid/setresuid without the
# matching privilege with an *uncatchable* SIGSYS before the syscall ever
# returns, which is observed from outside as exit 159 / "Bad system call".
# Stock Linux happily performs those calls, so on any Linux CI runner a build
# that still emits them looks perfectly healthy: M1 sees the injected byte
# arrive (ioctl(TIOCSTI) happens *before* the trailing seteuid) and the exit
# status is 0.  That is exactly how the unguarded call site in put_conn()
# survived the previous test suite.
#
# SECCOMP_RET_TRAP reproduces the boundary faithfully: the kernel delivers
# SIGSYS to the trapping process, so an image that issues one of those
# syscalls dies exactly as it would on HarmonyOS, while a fully guarded image
# issues none and is untouched.  Installing the filter in the child before
# execve is what makes the assertion bite.

_BPF_LD, _BPF_W, _BPF_ABS = 0x00, 0x00, 0x20
_BPF_JMP, _BPF_JEQ, _BPF_K = 0x05, 0x10, 0x00
_BPF_RET = 0x06

_SECCOMP_RET_KILL_PROCESS = 0x80000000
_SECCOMP_RET_TRAP = 0x00030000
_SECCOMP_RET_ALLOW = 0x7FFF0000

_PR_SET_NO_NEW_PRIVS = 38
_SECCOMP_SET_MODE_FILTER = 1
_SECCOMP_MODE_FILTER = 2

_AUDIT_ARCH = {"x86_64": 0xC000003E, "aarch64": 0xC00000B7}
_SECCOMP_NR = {"x86_64": 317, "aarch64": 277}

# The whole set*-id family.  glibc implements seteuid() through setresuid()
# where available and setreuid() otherwise, so all of them are trapped to stay
# correct across libc versions and architectures.
_SETID_NRS = {
    "x86_64": (105, 106, 113, 114, 117, 119, 161, 163),      # uid/gid/reuid/regid/resuid/resgid/fsuid/fsgid
    "aarch64": (146, 144, 145, 143, 154, 155, 165, 166),
}


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_uint16), ("jt", ctypes.c_uint8),
                ("jf", ctypes.c_uint8), ("k", ctypes.c_uint32)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort),
                ("filter", ctypes.POINTER(_SockFilter))]


class SeccompUnavailable(Exception):
    """The kernel or container refused a seccomp filter."""


def _install_setid_trap():
    """Arm the filter in the calling process; returns the trapped syscall list."""
    machine = os.uname().machine
    if machine not in _SETID_NRS:
        raise SeccompUnavailable("unsupported arch %s" % machine)
    nums = sorted(_SETID_NRS[machine])
    n = len(nums)

    # [0] A = arch, [1] right arch ? -> 3, [2] kill foreign-arch, [3] A = nr
    ins = [
        _SockFilter(_BPF_LD | _BPF_W | _BPF_ABS, 0, 0, 4),
        _SockFilter(_BPF_JMP | _BPF_JEQ | _BPF_K, 1, 0, _AUDIT_ARCH[machine]),
        _SockFilter(_BPF_RET | _BPF_K, 0, 0, _SECCOMP_RET_KILL_PROCESS),
        _SockFilter(_BPF_LD | _BPF_W | _BPF_ABS, 0, 0, 0),
    ]
    # Chain of comparisons at 4 .. 4+n-1: a match jumps to trap_at, a miss
    # falls through to the next comparison (jf = 0).  Falling off the end of
    # the chain reaches ALLOW, so unrelated syscalls pass untouched.
    trap_at, allow_at = 5 + n, 4 + n
    for i, num in enumerate(nums):
        at = 4 + i
        ins.append(_SockFilter(_BPF_JMP | _BPF_JEQ | _BPF_K,
                               trap_at - at - 1, 0, num))
    ins.append(_SockFilter(_BPF_RET | _BPF_K, 0, 0, _SECCOMP_RET_ALLOW))
    ins.append(_SockFilter(_BPF_RET | _BPF_K, 0, 0, _SECCOMP_RET_TRAP))

    arr = (_SockFilter * len(ins))(*ins)
    prog = _SockFprog(len(ins), ctypes.cast(arr, ctypes.POINTER(_SockFilter)))
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6",
                           use_errno=True)
    except OSError as exc:
        raise SeccompUnavailable("cannot load libc: %s" % exc)
    libc.prctl.restype = ctypes.c_int

    if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise SeccompUnavailable("PR_SET_NO_NEW_PRIVS failed (errno %d)"
                                 % ctypes.get_errno())
    ctypes.set_errno(0)
    if libc.syscall(_SECCOMP_NR[machine], _SECCOMP_SET_MODE_FILTER,
                    _SECCOMP_MODE_FILTER, ctypes.byref(prog)) != 0:
        raise SeccompUnavailable("seccomp(SET_MODE_FILTER) failed (errno %d)"
                                 % ctypes.get_errno())
    return nums


def _case_no_setid_syscall(binpath):
    """H5: drive a real keystroke injection with the E051 boundary enforced.

    This is the regression guard for the third seteuid() call site -- the
    "drop root privs again" tail of put_conn(), which every injected keystroke
    goes through.  Asserting only on the exit status is not enough (the byte is
    delivered before that call runs), so the boundary is enforced instead.
    """
    try:
        master, slave = pty.openpty()
    except OSError as exc:
        record("H5_no_setid_syscall_on_injection_path", False,
               "no pty available: %s" % exc)
        return
    slave_name = os.ttyname(slave)

    hook_r, hook_w = os.pipe()
    script = [b"Z", b"\x01", b"list\r", b"exit\r"]
    rc, out = run_pty([binpath, slave_name], script, settle=0.6, tail=1.5,
                      pre_exec=_install_setid_trap, hook_err=hook_w)
    os.close(hook_w)
    hook_err = b""
    try:
        os.set_blocking(hook_r, False)
        while True:
            chunk = os.read(hook_r, 4096)
            if not chunk:
                break
            hook_err += chunk
    except (BlockingIOError, OSError):
        pass
    os.close(hook_r)

    if hook_err:
        # The filter could not be armed, so nothing was actually enforced.
        # Report it as skipped rather than quietly passing a vacuous check.
        skip("H5_no_setid_syscall_on_injection_path",
             "seccomp filter not available on this host (%s); the privileged-id "
             "syscall boundary could not be enforced"
             % hook_err.decode("utf-8", "replace").strip())
        for fd in (master, slave):
            try:
                os.close(fd)
            except OSError:
                pass
        return

    delivered = b""
    try:
        os.set_blocking(master, False)
        time.sleep(0.2)
        while True:
            chunk = os.read(master, 4096)
            if not chunk:
                break
            delivered += chunk
    except (BlockingIOError, OSError):
        pass

    killed_by_sigsys = rc == -31
    ok = (not killed_by_sigsys and rc == 0 and b"Z" in delivered
          and "failed to drop root privs" not in out)
    record("H5_no_setid_syscall_on_injection_path", ok,
           "rc=%s sigsys=%s injected_byte=%s; %s"
           % (rc, killed_by_sigsys, b"Z" in delivered,
              "died by SIGSYS => at least one privileged-id syscall was emitted"
              if killed_by_sigsys
              else "survived => zero privileged-id syscalls on this path"))

    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass


def _summary():
    return json.dumps({
        "executed": True,
        "passed": not FAILED,
        "discovered": len(PASSED) + len(FAILED),
        "passedCount": len(PASSED),
        "failed": FAILED,
        "skipped": SKIPPED,
    })


if __name__ == "__main__":
    sys.exit(main())
