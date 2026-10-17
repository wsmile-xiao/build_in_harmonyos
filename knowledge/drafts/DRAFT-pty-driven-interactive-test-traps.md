# DRAFT-pty-driven-interactive-test-traps — 用 pty 自动化测试交互式程序的三个必踩坑

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: testing / pty / curses / terminfo / automation

## 相关既有条目（同族差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E028** | 讲 Linux 端「ncurses 必须静态库」的**编译要求**（`--without-shared`）。本条讲**静态链接 ncurses 的运行期后果**：程序启动时需在磁盘上找到**可读**的 terminfo 数据库，否则直接拒绝启动 |
| `operations/dependencies.md` / `operations/python-extensions.md` | 均只讲**编译期**链接方式（实测其 `terminfo` 相关命中 **0**）|

> 查重（2026-09-12）：`cannot initialize terminal type` 命中 **0**；`terminfo` 命中 **0**；`pty` 的 145 条命中中**无一条**讲用 `pty.fork` 驱动交互程序做自动化测试（按 `pty\.fork｜pty 驱动｜openpty` 交叉过滤命中 **0**）。

## Scope（何时用）

用 pty / expect 自动化测试**交互式程序**（curses/TUI、密码提示、shell 集成）时。

## 根因：pty 是双向异步的，缺少显式同步就必然出错

交互式程序无法用普通管道驱动（需要 tty：`isatty` 为真、可做终端控制），故用 pty。但由此产生**三类坑**，都会造成**假失败或假通过**。

### 坑一：curses 必须"等渲染完"再输入，且用 `\r` 确认

curses 初始化（`initscr`/`setupterm`）与首帧绘制需要时间；过早写入会被行规程缓冲吞掉或落在初始化前。实测把命令与口令一次性灌入 → `GETPIN` **返回空**。

另：curses 下确认键是 **`\r`（回车）**，只发 `\n` **不生效**。

```
等进程起来 → 发命令 → 【等渲染】 → 写输入 → \r
```

> 更稳的做法：**读输出直到出现预期提示**再输入（`read_until`），而非固定 `sleep` —— 固定 sleep 在慢机上仍会假失败。

### 坑二：不可把"退出命令"与"交互命令"同批发出

把 `BYE` 与 `GETPIN` 写进同一批 → 进程在**用户输入之前**就收到 BYE 并关闭连接 → `GETPIN` **永远拿不到数据**。

实测对照（同一二进制、同一输入）：

| 发送方式 | 结果 |
|---------|------|
| `BYE` 与 `GETPIN` **同批** | ❌ 失败 |
| `BYE` 与 `GETPIN` **不同批** | ✅ 成功 |

> 同样地，任何"结束/关闭"类命令都必须留到交互完成之后。

### 坑三：断言假阳性 —— `"OK"` 不代表业务成功

许多行式协议**握手首行本身就是成功串**（Assuan 为 `OK Pleased to meet you`）。于是：

```python
assert "OK" in output     # ✗ 进程刚起来还没执行任何命令时就为真 → 恒 PASS
```

必须断言**业务数据行**或**错误行**：

```python
assert b"D 1234" in out   # ✓ 数据行
assert b"ERR" in out      # ✓ 错误行
```

### 附带（curses 特有）：静态链接 ncurses → 需要**可读的** terminfo

**静态链接 ncurses 的程序**在运行期需要磁盘上存在 terminfo 数据库，否则**根本不启动**：

```
ncurses: cannot initialize terminal type ($TERM="xterm"); exiting
```

⚠️ **"目录存在" ≠ "可读"** —— 交叉构建产出的 terminfo 文件 owner 常为构建用户且权限收紧（实测 `-rw-rw----`）。须**实测可读性**后再选定 `TERMINFO`。

## 方案：四条硬性规则

### ① 先等渲染、再输入，用 `\r` 确认

`\n` 在 curses 下不生效。更稳的是**读到预期提示再写**（`read_until`）。

### ② 结束/关闭类命令（`BYE` 等）留到交互完成之后

绝不与交互命令同批发出。

### ③ 断言业务数据行或错误行

绝不断言通用成功字（`OK`）。若输出无结构化数据行，则断言"错误串**不**出现"作为下限。

### ④ 终端不可用时**如实标 SKIP 并计数**

不要让它变成 FAIL，更不要让它**静默算作 PASS**（R34）。

### 配套：机器可解析汇总行

```
RESULT: passed=N failed=M skipped=K
```

由 `test_package` 解析：`failed>0` / `passed==0` → **报错**；`skipped>0` → **告警**（让"没测到"可见）。

### 代码骨架

```python
pid, fd = pty.fork()
if pid == 0:
    os.execv(BIN, [os.path.basename(BIN)])

def read_until(pat, timeout=15):
    buf = b""; end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.3)
        if r:
            try: c = os.read(fd, 65536)
            except OSError: break
            if not c: break
            buf += c
            if re.search(pat, buf): break
    return buf

os.write(fd, b"SETDESC Enter PIN\nSETPROMPT PIN:\nGETPIN\n")
read_until(rb"(?i)pin:")      # ① 等渲染/等提示
os.write(fd, b"1234"); time.sleep(.4)
os.write(fd, b"\r")           # ① 回车确认（非 \n）
out = read_until(rb"D \d+") or read_until(rb"ERR")
assert b"D 1234" in out       # ③ 断言数据行，非 "OK"
# ④ BYE 留到最后，绝不与 GETPIN 同批
```

## 备选（fallback）

若环境**确实**无法提供可用终端（CI 无 pty、无可读 terminfo），把交互类断言**标 SKIP 并计数**，只运行不依赖终端的断言（握手、GETINFO、错误处理等），并在汇总行与 `test_note` 中**明确写出跳过了什么、为什么**。

> 底线：**绝不**把 `skipped` 并入 `passed`，也**绝不**因为"跑不了"就删掉这些断言（删掉等于失去覆盖且不留痕）。

## 禁止

- ❌ **一次性写入全部命令再读** —— 交互程序按提示逐步消费输入；一次性灌入会因渲染未完成/行规程缓冲而丢失，且 curses 下 `\n` 不是确认键（须 `\r`）→ 间歇性假失败（慢机上必现），最易被误判为"被测程序有 bug"
- ❌ **`BYE` 与 `GETPIN` 同批发出** —— 结束命令会立即关闭连接，使后续交互永远拿不到数据（实测同批→失败、不同批→成功）→ 交互断言必然失败，且原因隐蔽（日志里只看到"没收到数据"）
- ❌ **`assert "OK" in output`** —— 行式协议握手首行常为成功串（如 Assuan 的 `OK Pleased to meet you`）→ 该断言在进程刚启动时为真、恒 PASS → **假阳性**（功能完全坏掉也照样"通过"，正是 R34 要防的）

## 实证

- **pinentry/1.3.3（PR #9638）** —— 用 pty 驱动 `pinentry-tty` / `pinentry-curses` 做 Assuan 协议功能测试，**16 项**断言。实测踩坑：
  - curses 须**等渲染完**再输入、且用 **`\r`** 确认（`\n` 不生效）
  - **`BYE` 与 `GETPIN` 同批 → 失败；不同批 → 成功**
  - 仅断言 `"OK"` 会匹配握手首行 `OK Pleased to meet you`（**假阳性**）
  - `pinentry-curses` **静态链接 ncurses**（`readelf -d` 的 `NEEDED` 只有 libassuan/libgpg-error/libc，**无 libncurses**；`nm` 可见 `initscr` 等符号）→ 须有**可读** terminfo，否则报 `ncurses: cannot initialize terminal type` 并退出；实测制品内 terminfo 为 `-rw-rw----`（owner 为构建用户），故须实测 `os.access(entry, R_OK)` 而非判断存在性
