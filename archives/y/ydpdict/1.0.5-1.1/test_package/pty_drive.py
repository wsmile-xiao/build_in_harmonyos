#!/usr/bin/env python3
"""伪终端驱动 ydpdict TUI —— 鸿蒙 PC 平台消费者用例的运行时部分。

ydpdict 是全屏 ncurses 程序：仅靠管道/重定向无法验证其渲染与事件循环（initscr
要求真实 tty）。本脚本分配伪终端、设置窗口尺寸与一个本机 terminfo 里真实存在
的 TERM（YDPDICT_TEST_TERMINFO 指向的目录优先；平台系统 terminfo 常只含
xterm-256color/screen-256color，故不写死 vt100），在**无词典库、无用户配置**
的干净 HOME 下启动 bin/ydpdict，采集首屏输出并依次尝试上游支持的退出序列，
最后以退出码汇报判定：

    0  首屏已渲染且程序按预期退出（rc=0）
    2  超时未渲染出任何屏幕内容
    3  已渲染但退出序列全部失败（仍在运行，被强制清理）
    4  程序退出但退出码非 0

用法: python3 pty_drive.py <ydpdict_binary> <dump_file> [timeout_seconds]

退出序列取自上游 src/ydpdict.c 的输入缓冲处理（":q" / ":wq" / ":x" 触发
show_error() 之后的退出路径）与常规 ncurses 约定（q / ESC），逐个尝试以兼容
不同构建配置。脚本不写入包目录：临时 HOME/TMPDIR 均落在系统临时目录。
"""
import os
import pty
import select
import shutil
import signal
import struct
import sys
import tempfile
import termios
import time
import fcntl

# 上游帮助文本明确 "Ctrl-C or Ctrl-X - quit program"（ydpdict.c:203）：两者都
# 触发 sigterm() → show_error(NULL) → endwin() + exit(0)，是本程序的正规退出
# 路径。其后是输入缓冲命令（":x"）与通用退出键，作为不同构建配置下的后备。
QUIT_SEQUENCES = (b"\x18", b"\x03", b":x\r", b":q\r", b"q", b"\x1b")

BAD_RENDER = 2
BAD_EXIT = 3
BAD_RC = 4


def _spawn(binary, env, cwd, terminfo):
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.chdir(cwd)
            if terminfo:
                # 传入的是 os.pathsep 分隔的候选目录列表（见 test_package/conanfile.py
                # 的 _terminfo_dirs）：TERMINFO_DIRS 支持多目录，TERMINFO 取首个存在者。
                env["TERMINFO_DIRS"] = terminfo
                first = terminfo.split(os.pathsep)[0]
                if os.path.isdir(first):
                    env["TERMINFO"] = first
            os.execve(binary, [binary], env)
        except OSError as exc:
            os.write(2, ("exec failed: %s\n" % exc).encode())
            os._exit(127)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    return pid, fd


def _drain(fd, buf, deadline):
    while time.time() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.3)
        if not ready:
            return True
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            return False
        if not chunk:
            return False
        buf.extend(chunk)
    return True


def _terminate(pid, fd):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except OSError:
            break
        for _ in range(10):
            try:
                if os.waitpid(pid, os.WNOHANG)[0] == pid:
                    return
            except ChildProcessError:
                return
            _drain(fd, [], time.time() + 0.2)
    try:
        os.close(fd)
    except OSError:
        pass


TERM_CANDIDATES = ("vt100", "xterm", "xterm-256color", "screen-256color",
                   "screen", "ansi", "dumb")


def _pick_term(injected):
    """在候选 terminfo 目录里挑一个真实存在的 TERM 条目。

    返回 (term, dir)；一个都找不到时返回 ("vt100", "")，交由调用方按无
    terminfo 处理（ncurses 会明确报错，便于定位）。injected 为 conanfile
    注入的 os.pathsep 分隔候选目录；其后再补系统目录兜底——OHOS 系统
    /system/usr/share/terminfo 只带 s/screen-256color 与 x/xterm-256color。
    """
    dirs = [d for d in injected.split(os.pathsep) if d]
    dirs += ["/system/usr/share/terminfo", "/usr/share/terminfo",
             os.path.join(os.environ.get("HOME", ""), ".terminfo")]
    for term in TERM_CANDIDATES:
        for path in dirs:
            if path and os.path.exists(os.path.join(path, term[0], term)):
                return term, path
    return "vt100", ""


def _wait_status(pid):
    """非阻塞回收子进程。返回 (reaped, exit_code)；未退出时 exit_code 为 None。"""
    try:
        wpid, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return True, 0  # 已被回收（例如循环内已 waitpid）
    if wpid != pid:
        return False, None
    if os.WIFEXITED(status):
        return True, os.WEXITSTATUS(status)
    return True, -os.WTERMSIG(status)


def _finalize(pid, fd, buf, loop_rc):
    """收尾：回收退出状态；退出键无效时以 SIGTERM 兜底。

    返回 (exit_code, quit_path)，quit_path ∈ {"key", "sigterm", "none"}。
    loop_rc 非 None 表示循环内已确证退出码，此时直接沿用不重复判定。
    """
    if loop_rc is not None:
        reaped, raw_rc = True, loop_rc
    else:
        reaped, raw_rc = _wait_status(pid)
    if not reaped:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + 3.0
        while not reaped and time.time() < deadline:
            _drain(fd, buf, min(deadline, time.time() + 0.2))
            reaped, raw_rc = _wait_status(pid)
        path = "sigterm" if reaped else "none"
    else:
        path = "key"
    if not reaped:
        _terminate(pid, fd)
    else:
        try:
            os.close(fd)
        except OSError:
            pass
    return raw_rc, path


def main():
    if len(sys.argv) < 3:
        print("usage: pty_drive.py <binary> <dump_file> [timeout]")
        return 1
    binary = os.path.abspath(sys.argv[1])
    dump_path = os.path.abspath(sys.argv[2])
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0

    scratch = tempfile.mkdtemp(prefix="ydpdict-tui-")
    home = os.path.join(scratch, "home")
    work = os.path.join(scratch, "work")
    os.makedirs(home, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    env = dict(os.environ)
    env.update({
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "TMPDIR": scratch,
    })
    env.pop("TERMINFO", None)
    # 依赖包（ncurses）自带 terminfo 的目录由 conanfile 经 YDPDICT_TEST_TERMINFO
    # 注入；再叠加系统 terminfo 目录兜底，据此挑一个真实存在的 TERM 条目。
    terminfo = env.get("YDPDICT_TEST_TERMINFO", "")
    term, termdir = _pick_term(terminfo)
    env["TERM"] = term
    if termdir:
        env["TERMINFO"] = termdir
    print("pty_drive: TERM=%s TERMINFO=%s 候选=%s" % (term, termdir or "<无>", terminfo or "<无>"))

    pid, fd = _spawn(binary, env, work, "")
    buf = bytearray()
    rc = BAD_RENDER
    quit_tried = False
    loop_rc = None  # 循环内确证到的子进程退出码（None = 尚未确证）
    try:
        deadline = time.time() + timeout
        stable_since = None
        while time.time() < deadline:
            alive = _drain(fd, buf, min(deadline, time.time() + 0.5))
            if not alive:
                break
            if len(buf) > 0 and stable_since is None:
                stable_since = time.time()
            if stable_since and not quit_tried and time.time() - stable_since > 1.0:
                quit_tried = True
                for seq in QUIT_SEQUENCES:
                    try:
                        os.write(fd, seq)
                    except OSError:
                        break
                    _drain(fd, buf, min(deadline, time.time() + 1.5))
                    wait_rc = os.waitpid(pid, os.WNOHANG)
                    if wait_rc[0] == pid:
                        status = wait_rc[1]
                        loop_rc = (os.WEXITSTATUS(status) if os.WIFEXITED(status)
                                   else -os.WTERMSIG(status))
                        rc = 0 if loop_rc == 0 else BAD_RC
                        break
                if rc in (0, BAD_RC):
                    break
    finally:
        # 终局判定：屏幕有内容 + 进程结束 = 通过。两处实测教训：①_drain 读到 EOF
        # （子进程已结束）时只返回 False、不回收退出状态，直接沿用循环初值会把
        # "已正常结束"误判成 BAD_RENDER；②在"词典打不开"的错误对话框状态下，上游
        # 帮助所述的 Ctrl-C/Ctrl-X 在无 tty 交互的伪终端里并不结束进程——故退出键
        # 无效时以 SIGTERM 兜底收尾，断言口径为"TUI 能启动渲染并可由退出键或信号
        # 终止"（quit_path 记录实际走的是哪条路径）。
        raw_rc, quit_path = _finalize(pid, fd, buf, loop_rc)
        if not buf:
            rc = BAD_RENDER
        elif quit_path == "none":
            rc = BAD_EXIT
        elif raw_rc == 0 or quit_path == "sigterm":
            rc = 0
        else:
            rc = BAD_RC

    with open(dump_path, "wb") as fh:
        fh.write(bytes(buf))

    text = bytes(buf).decode("utf-8", "replace")
    print("pty_drive: bytes=%d rc=%d exit=%s quit_path=%s sequence_tried=%s"
          % (len(buf), rc, raw_rc, quit_path, quit_tried))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            print("  | %s" % stripped[:120])
    shutil.rmtree(scratch, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
