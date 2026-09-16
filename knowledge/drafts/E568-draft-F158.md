# E568 — 上游 Python 包/测试把临时文件路径硬编码 /tmp（OHOS 只读挂载）；setsid 仅以 busybox applet 存在

## 错误特征

构建期运行上游 pytest 时出现两类失败（同一平台根因家族）：

```
OSError: [Errno 30] Read-only file system: '/tmp/afl_multicore.PGID.unittest_sess_01'
FileNotFoundError: [Errno 2] No such file or directory: 'setsid'
```

前者来自产品代码/测试把临时文件路径写死为 `/tmp/...`；后者来自 `subprocess.Popen(['setsid', ...])`。

## 触发条件

- 平台：OpenHarmony / HarmonyOS PC（aarch64），`/tmp` 为只读挂载（erofs, ro；SKILL E002）
- 构建系统：纯 Python（setuptools/pip）包，conan `build()` 内真实运行上游 pytest 套件（R51）
- 阶段：testing
- 触发源：产品代码或上游测试**硬编码 `/tmp`**；或 spawn util-linux 小工具（`setsid`/`pgrep`/`kill`）而系统未提供独立可执行文件

## 根因分析

1. **`/tmp` 只读**：OHOS 设备 `/tmp` 为只读挂载，任何 `open("/tmp/...", "a")` 都是 `OSError [Errno 30]`。上游把临时文件（本例 PGID 文件）路径硬编码 `/tmp`，因此该工具在本平台**根本不可用**——这是移植缺陷，不是「不可修复的平台限制」。
2. **`setsid` 缺失**：本机不提供独立的 `setsid` 可执行文件，但它作为 **busybox applet** 存在（`/data/service/hnp/bin/busybox --list | grep setsid` → `setsid`）。busybox 依 `argv[0]` 分派 applet，故一个名为 `setsid` 的软链指向 busybox 二进制即表现为真 `setsid`。

实测证据：

```
$ python3 -c "socket.create_connection(('api.twitter.com',443),…)"  # 无关，仅示例
$ PATH=$SHIM:$PATH setsid python3 -c "import os; print(os.getpid(), os.getpgid(0))"
22003 22003          # shim setsid 可真实 spawn 新会话进程
```

## 解决方案

### 推荐方案（产品代码可移植性修复 + 构建期 shim）

1. 产品代码把硬编码 `/tmp` 改为 `tempfile.gettempdir()`（遵循 `$TMPDIR`），并同步修改上游测试用例为**同一口径**（否则「产品写 TMPDIR、测试查 /tmp」永久不一致）；改动以 `patches/*.patch` 落地，无平台宏。
2. 构建期生成**私有 shim 目录**：`setsid → $(command -v busybox)`、`python → $(command -v python3)`，置于测试 `PATH` 最前（best-effort：找不到 provider 就跳过，不制造回归）。
3. 运行环境 `export TMPDIR=$HOME/tmp`，使 `tempfile.gettempdir()` 指向可写目录。

```
export TMPDIR=$HOME/tmp
SHIM=$TMPDIR/shim; mkdir -p $SHIM
ln -sf "$(command -v busybox)" $SHIM/setsid
ln -sf "$(command -v python3)" $SHIM/python
PATH=$SHIM:$PATH python3 -m pytest tests
```

### 禁止做法

- ❌ 把 `/tmp` 只读、`setsid` 缺失直接判为「不可修复的平台限制」而放弃——二者在配方内均可合法修复。
- ❌ 用 skip/伪造通过率掩盖失败（R51 明禁）。
- ❌ 在补丁或 conanfile 里注入 `__OHOS__` 平台宏（PF5）绕路。

## 验证

```bash
cd archives/a/afl-utils/1.35a
export TMPDIR=$HOME/tmp
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
# → rc 0；UPSTREAM-PYTEST-SUMMARY: 92 passed, 1 warning …（0 failed / 0 skipped）
```

## 关联条目

- 相关: E002（/tmp 只读）、E547（libcheck P_tmpdir 优先级，同为临时目录/只读 trap）
- 相关: E569（conan basic_layout copytree 自递归）
