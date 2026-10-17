#!/usr/bin/env python3
"""pinentry 上游接口功能测试（Assuan 协议）—— pinentry 1.3.3 适配配套

⚠️ 为什么不是 `make check`：
   pinentry 1.3.3 官方 tarball **不含 tests/ 目录**。实测证据（2026-09-12）：
     · `tar tf pinentry-1.3.3.tar.bz2 | grep -i test` → **0 条**
     · 顶层 `SUBDIRS`（Makefile.am:114）不含 tests
     · 全树 `grep -rn '^TESTS\\|check_PROGRAMS'` → **无任何匹配**
   → `make check` 是 **no-op**，上游**没有可跑的自动化测试套件**。
   因此本脚本直接驱动**上游真实对外接口** —— gpg-agent 与 pinentry 之间使用的
   Assuan 协议（命令表见 `pinentry/pinentry.c`）。

覆盖（2 个前端 × 8 项 = 16 项）：
   A. 启动握手 + GETINFO（version / pid）           —— 不依赖终端
   B. 协议错误处理（未知命令 / GETINFO 参数错误）   —— 不依赖终端
   C. 交互命令（GETPIN / CONFIRM / MESSAGE）        —— **依赖可用的终端**

终端依赖与 SKIP 语义：
   pinentry-curses **静态链接 ncurses**（`NEEDED` 里无 libncurses），必须能读到
   terminfo 数据库才能初始化终端。若不可用会打印
   `ncurses: cannot initialize terminal type ($TERM="…"); exiting`。
   此时 C 类断言标为 **SKIP**（环境限制）而非 FAIL，并计入汇总 —— 本脚本绝不把
   "跑不了" 当作 "通过"（R34）。

用法：
  LD_LIBRARY_PATH=<pkg>/lib:<libassuan>/lib:<libgpg-error>/lib \
    python3 run_upstream_tests.py --bindir <pkg>/bin [--verbose]

汇总行格式（供上层 conanfile 断言）：
  RESULT: passed=N failed=M skipped=K
退出码：failed > 0 → 1，否则 0。
"""
import argparse
import os
import pty
import re
import select
import subprocess
import sys
import time

BIN = None
PASS, FAIL, SKIP = [], [], []


def record(name, status, detail=""):
    bucket = {"pass": PASS, "fail": FAIL, "skip": SKIP}[status]
    bucket.append(name)
    tag = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[status]
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""), flush=True)


def _terminfo_entry(d, term):
    """判断目录 d 内是否存在**当前用户可读**的 term 条目。

    返回匹配到的布局名（"classic"/"flat"/"hashed"），无则 None。

    terminfo 有三类布局（实测 conan 的 ncurses 制品两种都出现过）：
      · classic：<d>/<term 首字符>/<term>           例：.../terminfo/x/xterm
      · flat   ：<d>/<term>                        例：.../terminfo/xterm
      · hashed ：<d>/<首字节两位十六进制>/<term>    例：.../terminfo/78/xterm

    ⚠️ 实测（同一份 3977 字节 xterm 数据、权限均放开、仅布局不同）：
        classic 布局 → pinentry-curses 可正常初始化终端（OK）
        hashed  布局 → 报 `ncurses: cannot initialize terminal type`（FAIL）
      故调用方应**优先选 classic/flat**，hashed 仅作兜底（见 find_terminfo）。

    另注：OHOS/HMDFS 上文件 owner 常为构建用户且 other 位被剥离，
    故必须实测 R_OK，不能只看文件存在。
    """
    hashed = format(ord(term[0]), "02x")
    for layout, rel in (("classic", os.path.join(term[0], term)),
                        ("flat", term),
                        ("hashed", os.path.join(hashed, term))):
        cand = os.path.join(d, rel)
        if os.path.isfile(cand) and os.access(cand, os.R_OK):
            return layout
    return None


def find_terminfo():
    """找一个**当前用户可读**、且含 $TERM 条目的 terminfo 目录。

    OHOS 的 HMDFS 上文件 owner 常为构建用户且 other 位被剥离，故必须实测可读性，
    不能只看目录是否存在。

    ⚠️ 选择策略（实测决定）：**优先 classic/flat 布局，hashed 仅作兜底** ——
    同一份 xterm 数据、权限均放开，仅布局不同时，classic 可让 pinentry-curses
    正常初始化终端，hashed 则报 `cannot initialize terminal type`。
    若单纯"先到先得"，会选中 conan 缓存里 hashed 的那个目录而使 curses 用例
    被多余 SKIP（正是本函数要避免的）。
    """
    term = os.environ.get("TERM") or "xterm"
    cands = []
    if os.environ.get("TERMINFO"):
        cands.append(os.environ["TERMINFO"])
    cands += [
        "/usr/share/terminfo", "/etc/terminfo", "/lib/terminfo",
        "/usr/lib/terminfo", "/data/service/hnp/share/terminfo",
    ]
    # conan 缓存里的 ncurses 制品（本机实测可用处）。
    # ⚠️ 注意路径层级：制品目录为 <root>/p/<pkgid>/<package|build|...>/，
    # 其中**包内容所在的子目录也叫 `p`**（b=build、s=source…），故 terminfo 在
    # `<root>/p/<pkgid>/p/{share,lib}/terminfo` —— 早期实现漏了这一级，
    # 导致 cands 全是无效路径、函数**恒返回 None**。
    for root in (os.environ.get("CONAN_HOME", ""),
                 os.path.expanduser("~/.conan2")):
        if not root:
            continue
        pkg = os.path.join(root, "p")
        if not os.path.isdir(pkg):
            continue
        for d in sorted(os.listdir(pkg)):
            for sub in ("p/share/terminfo", "p/lib/terminfo"):
                cands.append(os.path.join(pkg, d, sub))

    # 这里**不设** TERMINFO 环境变量，避免解析顺序不确定性影响其结果。
    # 让每个候选目录返回自身可用的布局，再按 classic > flat > hashed 择优。
    # 注意：cands 中靠前的是**环境显式指定**的 TERMINFO 与系统目录，
    # 它们若可用应优先尊重（用户显式指定优先），故按「布局等级」稳定排序、
    # 同级保持原有先后顺序。
    _rank = {"classic": 0, "flat": 1, "hashed": 2}
    found = []
    for idx, d in enumerate(cands):
        layout = _terminfo_entry(d, term)
        if layout:
            found.append((_rank[layout], idx, d, layout))
    if not found:
        return None
    found.sort()
    return found[0][2]


def run_plain(binary, commands, timeout=12):
    inp = "".join(c + "\n" for c in commands)
    p = subprocess.run([os.path.join(BIN, binary)], input=inp,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _read_until(fd, pat, timeout=8.0, out=b""):
    """读取直到 pat 出现或超时；返回累计输出（事件驱动，不用固定 sleep）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                c = os.read(fd, 65536)
            except OSError:
                break
            if not c:
                break
            out += c
            if re.search(pat, out):
                break
    return out


def _drain(fd, idle=1.0, timeout=20.0, out=b""):
    """读到「连续 idle 秒无新数据」为止（收尾用，替代固定 sleep）。"""
    deadline = time.time() + timeout
    last = time.time()
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                c = os.read(fd, 65536)
            except OSError:
                break
            if not c:
                break
            out += c
            last = time.time()
        elif time.time() - last >= idle:
            break
    return out


def count_ok_lines(out):
    """统计 Assuan 的整行 OK 响应数。

    握手本身就会回一行 `OK Pleased to meet you`，且每个**命令成功**各回一行 OK，
    因此**单看 "OK" 是否出现等价于恒真**（这是本测试早期的假阳性来源）。

    归一化的必要性（实测）：
      · curses 前端退出时会把响应 OK 紧接在终端转义序列之后、且以 `\\r` 分隔
        （形如 `...\\x1b[?1l\\x1b>OK\\r\\n`）→ 直接按 `^OK` 匹配会**少算一行**；
      · 故先剥离 ANSI 转义、再把 `\\r` 归一为 `\\n`，才能对两种前端一视同仁。
    """
    text = out
    # 剥离常见 ANSI/VT 转义（CSI、字符集选择、OSC 等）
    text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)
    text = re.sub(r"\x1b[()][A-Z0-9]", "", text)
    text = re.sub(r"\x1b[>=NOP]", "", text)
    text = re.sub(r"\x1b\][^\x07]*\x07", "", text)
    # `\r` 也是行分隔符（curses 退出路径），归一为 `\n`
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return len(re.findall(r"(?m)^OK\b.*$", text))


# 断言用的最小 OK 行数：握手(1) + SETDESC(1) + 被测命令(1) = 3。
# 取 3 而非 2 —— 因为测试都先发 SETDESC 再发被测命令，若只取 2，
# 则「握手 + SETDESC」两行即可满足阈值，被测命令返回 ERR 时仍会通过（假阳性）。
MIN_OK_LINES = 3


def run_pty(binary, commands, steps=(), timeout=20):
    """pty 驱动交互命令（**事件驱动同步，不使用固定 sleep**）。

    steps: [(answer, wait_pat), ...] —— 先读输出直到 wait_pat（确认界面已渲染），
           再写 answer 并以 '\\r' 确认。慢 CI 上不会因 sleep 过短假失败，也不会
           因 sleep 过长拖慢。

    时序要点（均由实测得出）：
      · 有提示时须**等渲染完**再输入，且用 '\\r' 确认（'\\n' 在 curses 下不生效）；
      · **不可**把 BYE 与交互命令同批发出 —— 连接会在用户输入前关闭，
        导致 GETPIN 永远拿不到数据（实测：同批→False，不同批→True）。
    """
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execv(os.path.join(BIN, binary), [binary])
        except Exception:
            os._exit(127)
    out = b""
    script = "".join(c + "\n" for c in commands).encode()
    try:
        out = _read_until(fd, rb"Pleased to meet you", 5.0, out)   # 等握手
        os.write(fd, script)
        for answer, wait_pat in steps:
            out = _read_until(fd, wait_pat, 8.0, out)               # 等提示渲染
            os.write(fd, answer.encode())
            time.sleep(0.15)
            os.write(fd, b"\r")                                     # 回车确认
        out = _drain(fd, idle=1.0, timeout=timeout, out=out)        # 收尾
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.waitpid(pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            pass
    return out.decode(errors="replace")


TERMINAL_BROKEN = "cannot initialize terminal type"


def main():
    global BIN
    ap = argparse.ArgumentParser()
    ap.add_argument("--bindir", required=True)
    args = ap.parse_args()
    BIN = args.bindir

    ti = find_terminfo()
    # 注意：不能写成 `if ti and not os.environ.get("TERMINFO")` —— 那样在环境
    # **已设 TERMINFO 但该目录不可用/不可读**时，会白白丢弃 find_terminfo() 实测
    # 到的可用目录，导致 curses 交互用例被**多余 SKIP**（覆盖缩小）。
    # 正确判据是「当前 TERMINFO 是否真的可用于本 TERM」：不可用才用实测值覆盖。
    if ti:
        cur = os.environ.get("TERMINFO")
        cur_ok = False
        if cur:
            term = os.environ.get("TERM") or "xterm"
            for cand in (os.path.join(cur, term[0], term), os.path.join(cur, term)):
                if os.path.isfile(cand) and os.access(cand, os.R_OK):
                    cur_ok = True
                    break
        if not cur_ok:
            if cur:
                print(f"   [info] 环境 TERMINFO={cur} 对 TERM="
                      f"{os.environ.get('TERM')} 不可用，改用实测可用目录")
            os.environ["TERMINFO"] = ti
    if not os.environ.get("TERM"):
        os.environ["TERM"] = "xterm"

    print(f"== pinentry 上游接口功能测试 (Assuan) ==  bindir={BIN}")
    print(f"   TERM={os.environ.get('TERM')}  TERMINFO={os.environ.get('TERMINFO') or '<无可用>'}\n")

    for binary in ("pinentry-tty", "pinentry-curses"):
        exe = os.path.join(BIN, binary)
        print(f"--- {binary} ---", flush=True)
        if not os.path.isfile(exe):
            record(f"{binary}: binary exists", "fail", "二进制缺失")
            continue
        record(f"{binary}: binary exists", "pass")

        # A. 握手 + GETINFO
        try:
            _, out, _ = run_plain(binary, ["GETINFO version", "BYE"])
            m = re.search(r"D (\d+\.\d+\.\d+)", out)
            record(f"{binary}: GETINFO version == 1.3.3",
                   "pass" if (m and m.group(1) == "1.3.3") else "fail",
                   f"got {m.group(1) if m else out.strip()[:40]}")
        except Exception as e:
            record(f"{binary}: GETINFO version == 1.3.3", "fail", str(e)[:60])

        try:
            _, out, _ = run_plain(binary, ["GETINFO pid", "BYE"])
            ok = re.search(r"^D \d+$", out, re.M) is not None
            record(f"{binary}: GETINFO pid returns number",
                   "pass" if ok else "fail",
                   next((l for l in out.splitlines() if l.startswith("D ")), "")[:30])
        except Exception as e:
            record(f"{binary}: GETINFO pid returns number", "fail", str(e)[:60])

        # B. 协议错误处理
        try:
            _, out, _ = run_plain(binary, ["NOSUCHCOMMAND", "BYE"])
            ok = "ERR" in out and "unknown" in out.lower()
            record(f"{binary}: unknown command -> ERR",
                   "pass" if ok else "fail",
                   next((l for l in out.splitlines() if l.startswith("ERR")), "")[:44])
        except Exception as e:
            record(f"{binary}: unknown command -> ERR", "fail", str(e)[:60])

        try:
            _, out, _ = run_plain(binary, ["GETINFO flavors", "BYE"])
            record(f"{binary}: malformed GETINFO arg -> ERR",
                   "pass" if "ERR" in out else "fail",
                   next((l for l in out.splitlines() if l.startswith("ERR")), "")[:44])
        except Exception as e:
            record(f"{binary}: malformed GETINFO arg -> ERR", "fail", str(e)[:60])

        # C. 交互命令 —— 先探测终端是否真的可用
        try:
            probe = run_pty(binary, ["SETDESC probe", "MESSAGE"])
            terminal_ok = TERMINAL_BROKEN not in probe
        except Exception:
            terminal_ok = False

        if not terminal_ok:
            for label in ("GETPIN returns entered PIN (D 1234)",
                          "CONFIRM accepts 'o'",
                          "MESSAGE renders and returns OK"):
                record(f"{binary}: {label}", "skip",
                       f"终端不可用（{TERMINAL_BROKEN}）")
        else:
            try:
                out = run_pty(binary,
                              ["SETDESC Enter PIN", "SETPROMPT PIN:", "GETPIN"],
                              steps=[("1234", rb"(?i)pin:")])
                # GETPIN 的断言以**数据行**为准：`D 1234` 只有在 GETPIN 真正成功
                # 并把用户输入的 PIN 回吐时才会出现（GETPIN 失败只会得到 ERR），
                # 故这已是强断言、且不受前置命令 OK 行影响。
                # ⚠️ 这里**不要**再叠加精确的 OK 行数阈值：实测在 TERM=dumb（CI 的
                # 默认 TERM）下，curses 的最后一个 OK 可能因 pty 收尾时序而偶发漏读
                # （同一场景手工抓包得 4 行、测试进程得 3 行），叠加阈值会造成**假失败**。
                ok = ("D 1234" in out) and "ERR" not in out
                record(f"{binary}: GETPIN returns entered PIN (D 1234)",
                       "pass" if ok else "fail",
                       f"data={re.findall(r'D [0-9]+', out)[:2]} ok_lines={count_ok_lines(out)}")
            except Exception as e:
                record(f"{binary}: GETPIN returns entered PIN (D 1234)", "fail", str(e)[:60])

            try:
                # CONFIRM 的提示是 `[o]?`（实测：回 'y' 会报 Invalid selection 并循环），
                # 确认键为 'o'。
                # 前置命令仅 SETDESC 1 条 → 成功时共 3 行 OK（握手 1 + 前置 1 + CONFIRM 1）。
                # ⚠️ 阈值必须取 3 而非 2：若取 2，则「握手 + SETDESC」两行即可满足，
                # 被测命令返回 ERR 时仍会 PASS（假阳性）—— 实测失败时恰好是 2 行。
                out = run_pty(binary, ["SETDESC Confirm?", "CONFIRM"],
                              steps=[("o", rb"\[o\]\?")])
                n_ok = count_ok_lines(out)
                ok = (n_ok >= 3 and "ERR" not in out
                      and "Invalid selection" not in out)
                record(f"{binary}: CONFIRM accepts 'o'",
                       "pass" if ok else "fail",
                       f"ok_lines={n_ok}")
            except Exception as e:
                record(f"{binary}: CONFIRM accepts 'o'", "fail", str(e)[:60])

            try:
                # MESSAGE 显示后要求按键继续（"Press any key to continue."），按键后才回 OK。
                # 前置命令仅 SETDESC 1 条 → 成功时共 3 行 OK；阈值取 3 的理由同 CONFIRM。
                out = run_pty(binary, ["SETDESC Message text", "MESSAGE"],
                              steps=[("", rb"(?i)any key")])
                n_ok = count_ok_lines(out)
                ok = n_ok >= 3 and "ERR" not in out
                record(f"{binary}: MESSAGE renders and returns OK",
                       "pass" if ok else "fail",
                       f"ok_lines={n_ok}")
            except Exception as e:
                record(f"{binary}: MESSAGE renders and returns OK", "fail", str(e)[:60])

    print(f"\nRESULT: passed={len(PASS)} failed={len(FAIL)} skipped={len(SKIP)}")
    if FAIL:
        print("失败项:")
        for f in FAIL:
            print(f"  - {f}")
    if SKIP:
        print("跳过项（环境限制，未计为通过）:")
        for s in SKIP:
            print(f"  - {s}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
