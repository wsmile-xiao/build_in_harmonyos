# DRAFT-8960 — conan test_package 中「被测 CLI 读 stdin 到 EOF」时 CI 常开 stdin 导致阻塞超时

- **条目 ID**: `DRAFT-8960-conan-test-package-cli-reads-stdin-to-eof`
- **严重度**: 2（🟡 中等）
- **类别**: conan, testing, cli-tool, non-interactive, portability
- **触发工具/阶段**: conan | test_package | python — testing / conan_build
- **来源**: kea-shell 3.0.3 适配（PR #10342 / CI build #48667）

## 错误特征

```
subprocess.TimeoutExpired: Command '[.../bin/kea-shell', '--host', '127.0.0.1', '--port', '45009',
    '--service', 'dhcp4', 'list-commands']' timed out after 60 seconds
ERROR: kea-shell/3.0.3 (test package): Error in test() method, line 28
[fail] kea-shell/3.0.3 — conan create failed        →  L1_RESULT=fail: conan create failed
CI 诊断侧多显示为「构建超时 — 可能是交互式测试卡住」
```

## 场景

`kea-shell`（ISC Kea 的 REST 客户端）把 stdin 上的可选参数拼进请求体：

```python
    # Read arguments from stdin (they're optional for some commands)
    for line in sys.stdin:
        params.args += line
```

**读到 EOF 才继续**——所以上游自己的进程测试一律写成 `echo | kea-shell …`（喂一个空行并关闭管道）。
首版 `test_package` 用 `subprocess.run([kea-shell, ...], capture_output=True)` 驱动它，没有给 stdin。

## 根因

1. 被测 CLI 的 stdin 语义是「可选参数，**读到 EOF 为止**」；不主动给 EOF 就无法结束读循环。
2. 测试侧 `subprocess.run()` **默认继承父进程 stdin**：本地是终端（EOF 立即到达）→ 通过；
   CI worker 的 stdin 是**永不关闭的管道**（buildbot/PTY）→ 子进程永远等不到 EOF → 永久阻塞。
3. CLI 内部的 `signal.alarm(timeout)` 兜底**无效**：它在该 stdin 循环**之后**才设置
   （`kea-shell.in` 顺序：parse → 版本早退 → 读 stdin → 建请求 → `signal.alarm` → 发送），
   阻塞发生在报警器武装之前。故这不是"程序缺陷"，而是"调用方式缺陷"。
4. 失败形态在 CI 侧被判为「构建超时 / 交互式测试卡住」，容易误导到 `make check --no-interaction` 方向。

## 推荐方案

```python
def run(*args, **kwargs):
    # kea-shell reads its optional extra arguments from stdin until EOF
    # ("for line in sys.stdin", kea-shell.in).  Without an explicit EOF the command
    # blocks forever whenever the caller's stdin stays open — which is exactly what
    # happens on the CI worker (upstream's own tests therefore always feed it: `echo | kea-shell`).
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run([SHELL, *args], capture_output=True, text=True, timeout=30, **kwargs)
```

- Python：`stdin=subprocess.DEVNULL`（推荐）；需要传数据时用 `input=payload, text=True`
  （`communicate()` 会关闭 stdin）。
- shell：`echo | cmd …` 或 `cmd … < /dev/null`。
- 子进程超时收紧到 30 s，同类问题更快暴露。

## 复现 / 自检

```bash
# 1) 让被测进程的 stdin 常开（不关闭 write 端）
python3 - <<'PY'
import subprocess, threading
p = subprocess.Popen([K, "--host","127.0.0.1","--port","1","list-commands"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
# 注意：不要调用 p.communicate()（它会替你关掉 stdin！），改为另起线程读 stdout + p.wait(timeout=8)
PY
# 修复前：阻塞 >8s ；stdin=DEVNULL：立即完成
# 2) 端到端（CI 等价条件）
python3 -c "import subprocess;p=subprocess.Popen(['conan','create','.'],stdin=subprocess.PIPE);print(p.wait())"
sleep 90 | python3 test_package/test_kea_shell.py
```

## 影响 / 回退 / 限制

- **影响**：任何"CLI 从 stdin 读取直到 EOF"的包（管理客户端、从 stdin 读 JSON 的工具、
  交互式安装器等）在 `test_package` / CI smoke test 中都会踩；**本地通过、CI 失败**是典型特征。
- **回退**：若被测 CLI 必须 TTY（如口令输入），不要在它上面做端到端断言，改为断言
  `--version` / `--help` 等不读 stdin 的路径，并在 notes 中写明范围。
- **限制**：仅覆盖"测试侧未给 EOF"；无 TTY 时行为异常的工具需另案（PTY 驱动类草稿）。

## 证据链（kea-shell 3.0.3）

- CI 失败日志：`subprocess.TimeoutExpired … timed out after 60 seconds` → `Error in test() method` →
  `L1_RESULT=fail: conan create failed`（PR #10342，build #48667）
- 本机精确复现（保持 stdin 常开且不关闭）：
  `[stdin=DEVNULL] 完成 rc=1` / `[stdin=常开管道（不关闭）] ❌ 阻塞 >8s`
- 修复后：`sleep 90 | python3 test_kea_shell.py` → `checks run: 12 / all checks passed`；
  以常开 stdin 管道运行 `conan create` → `EXIT_CODE = 0`
- 反证：上游 `.sh` 测试均写 `echo | kea-shell …`

## 关联条目

- **E214**（Shell 脚本交互式 `read` 阻塞非交互式执行）——同一族问题：非交互环境下等待
  stdin 导致阻塞；E214 的处置在**工具侧**（`read < /dev/null` 等），本条目补充**测试侧**
  （驱动方显式给 EOF）的对应做法。
