# DRAFT-13336-rainfrog-toolchain-probe-exec-not-access — 工具链可用性探测**不能用 `os.access(X_OK)`**：权限位说「可执行」而实际 `exec` 被拒，探测层必须真跑一次

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: 🟠 high（探测层误判会让构建**当场崩**，且掩盖应有的回退路径） | **Category**: conan / ohos / rust / toolchain-provisioning

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条增量（差异化） |
|---------|---------|--------|--------------------|
| `DRAFT-below-ohos-unsigned-rust-toolchain` | 已收 | **被拒的原因**：未签名 ELF 无法 `execve`（errno 13）；并给出"先怀疑未签名，不要再查 mode 位"的一行判据 + 自签名修复 | 它讲**原因的判定**；本条讲**探测/决策层**——`os.access` 会**谎报可执行**，因此"有没有可用工具链"这个问题**只能用真跑一次来回答**。两者互补：先知道"为何被拒"，再知道"如何可靠地判断可用性" |
| `E232` / `DRAFT-libisal-2.31.1-*` / `DRAFT-yices-2.7.0-*` | 已收 | `configure`/`dist/bin` 下的二进制 exec 被拒（HMDFS 拒脚本直接执行、EACCES） | 场景是"要执行的**构建脚本/产物**"，本条是"**选择用哪个工具链**"的探测步骤 |
| `wagyu-0.6.1-rust-legacy-lockfile-ohos-port` | 已收 | 记录过 `openssl@3-3.6.3` 实测 404、pin 须当日实测可达 | 那条讲 **URL 会过期**；本条讲"**工具链到底能不能用**"的判定方式（可用性 ≠ 存在性 ≠ 权限位） |

> **查证记录**（四路检索 `graph/index.tsv` / `graph/*.kv` / `doc/*.md` / `drafts/*`）：
> `os.access` / `X_OK` 命中 21 个文件，逐一看过：其中 14 个讲"exec 被拒"（原因层），
> 5 个讲路径/符号链接前置，**无一处**把"`os.access` 返回 True 但 exec 失败"作为
> **探测方法论**提出。`os.access 返回 True 却 exec 失败` 这一组合命题命中 **0**。

## Scope（何时用）

任何**先探测工具链/工具是否可用、再决定用它或回退到 bootstrap** 的配方，典型形态：

```python
if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
    return cand          # ← 在 OHOS 上这一步会给出错误答案
```

尤其当配方存在"引导/回退"分支（如从 bottle 装一套自包含工具链）时——探测误判会让
**回退分支永远不被走到**，构建直接崩在第一个真正 `exec` 的地方。

## Symptom

探测认为工具可用，随后 `subprocess` 调用立刻抛异常，且**假象是"工具存在"**：

```text
ERROR: rainfrog/0.3.20: Error in build() method
  PermissionError: [Errno 13] Permission denied:
  '/storage/Users/currentUser/usr/local/bin/cargo'
```

排查现场（同一文件，两种结论）：

```python
os.path.isfile(p)      # True
os.access(p, os.X_OK)  # True        ← 权限位看着可执行
subprocess.run([p,"--version"])       # PermissionError: [Errno 13]
```

```sh
$ ls -l /storage/Users/currentUser/usr/local/bin/cargo
-rwxr-x--- 1 20001006 file_manager 43714728 ... cargo
#      ^^^ 组可执行 → os.access 以"当前用户属该组"判定 True
```

## 根因

两层原因叠加，缺一都不成立：

1. **权限位与"能否 exec"不等价**。`os.access(X_OK)` 完全基于 POSIX mode 位与
   uid/gid 关系判断，**不涉及** OHOS 的额外执行约束（未签名 ELF / 域与挂载的
   执行策略）。文件 `0o750`、组 `file_manager`，而 `os.access` 认为当前用户可用
   → 返回 True；真正 `execve` 时才被内核/loader 拒绝。
2. **配方的"回退"逻辑被探测短路**。这类配方普遍写成
   "找到可用工具链就用它，否则 bootstrap"。探测误判 ⇒ 永远走不到 bootstrap ⇒
   一崩了事，**现场看不到"其实可以引导一套可用的"**。

> 注意与 `DRAFT-below-*` 的边界：那条解决"**被拒之后怎么办**"（签名/拷到可写位置）；
> 本条解决"**如何不误判**"（探测方式）。**只做签名不做探测修正，仍会误判**；
> 只做探测修正不签名，会正确回退但引导出来的工具链若未签名仍不可用——**两者都要**。

## 修复（rainfrog 0.3.20 实证）

把探测从"查权限位"改为"**真跑一次并查退出码**"：

```python
@staticmethod
def _runnable(path, name):
    """Probe a tool by ACTUALLY executing it — never by os.access()."""
    if not path or not os.path.isfile(path):
        return False
    try:
        proc = subprocess.run([path, "--version"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and name in (proc.stdout or "") + (proc.stderr or "")
```

于是设备上那个"看着可执行"的 cargo 被正确判为**不可用**，配方随即退到 bottle 引导，
`conan create` 一次通过（实测：67/67 上游测试 + 4/4 消费者断言）。

**代价与取舍**：真跑一次比查权限位慢（一次进程启动，~10–50ms），且要求
`--version` 是安全的只读操作——对 cargo/rustc/编译器/git 这类工具成立。若某工具的
`--version` 有副作用，改用 `--help` 或 `-V` 等更保守的探测参数。

## 适用范围

- **所有"探测 + 回退 bootstrap"式配方**（本仓 Rust 系最集中：约 19 个配方用
  harmonybrew bottle 引导，多数沿用 `os.access` 写法）；
- 任何在 OHOS 上判断"外部工具/预编译产物能否执行"的代码；
- 通用判据：**存在性（isfile）≠ 权限可执行（access）≠ 真能执行（exec）**，
  在 OHOS 上三者必须分开验证，第三项只能用真跑。

## 反例/边界

- 若工具**确实**可用，真跑探测只多一次进程开销，无副作用——没有理由为省这点开销而冒险。
- 探测失败有多种原因（未签名、域策略、缺动态库、架构不符），**本条只要求"不要误判为可用"**；
  具体原因归因见 `DRAFT-below-*`（未签名）、E232 家族（HMDFS 拒脚本直接执行）等。
- 对**被测工具本身**（如 cargo 需要 `libssl.so`）的依赖缺失导致的失败，属"能 exec 但起不来"，
  不是本条的"探测说能 exec 其实不能"，需分别处理（见 below 草稿"错误 2"）。

## 触发实例

rainfrog 0.3.20（PR #13336，2026-09-27）。首版照抄 `alass/2.0.0` 的 `os.access`
探测 → `conan create` 崩在 `PermissionError: .../usr/local/bin/cargo`；改为实执行探测后
正确回退到 bottle 引导并一次构建通过。同机另查：无其它可用 rust
（`usr/rust-*`、`~/.harmonybrew`、`hnp`、`app` 均不存在），故该回退是**唯一路径**，
被误判短路后没有任何"另一条路"可走。
