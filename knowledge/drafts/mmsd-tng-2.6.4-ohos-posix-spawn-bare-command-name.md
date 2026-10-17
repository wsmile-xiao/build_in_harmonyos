# OHOS libc 的 posix_spawn 不按 PATH 解析裸命令名 → 构建工具链必须绝对路径

> 草稿 ID：`mmsd-tng-2.6.4-ohos-posix-spawn-bare-command-name`
> 来源任务：mmsd-tng 2.6.4 适配（HarmonyOS PC aarch64 / meson 1.11.0 / clang 15.0.4）

## 错误特征

```
ERROR: Unknown compiler(s): [['clang']]
The following exception(s) were encountered:
Running `clang --version` gave "[Errno 2] No such file or directory: 'clang'"
```

最迷惑的地方：**文件就在 PATH 里，shell 里执行完全正常**：

```bash
$ /data/service/hnp/bin/clang --version
clang version 15.0.4 …  Target: aarch64-unknown-linux-ohos       # exit=0
$ echo $PATH | tr ':' '\n' | grep hnp
/data/service/hnp/bin
```

## 触发条件

- 在 HarmonyOS/OHOS 主机上做构建（原生或交叉）；
- 工具链以**裸命令名**传入：环境变量 `CC=clang` / `AR=llvm-ar` / …，
  或构建系统 native/cross 文件的 `[binaries] c = clang` / `ar = llvm-ar`；
- 构建系统把该值**原样拿去 Popen**（Meson 的编译器探测就是如此）。

## 根因

Python `subprocess` 在 OHOS 上走 `os.posix_spawn`，其 PATH 查找语义与 POSIX shell 的
`execvp` 不同——传入不含 `/` 的裸名时不会（可靠地）在 PATH 中检索，直接以 ENOENT 失败。

实测对照（同一 shell、同一 PATH）：

| 调用 | 结果 |
|---|---|
| `shutil.which("clang")` | `/data/service/hnp/bin/clang` ← **Python 自己找得到** |
| `subprocess.run(["clang","--version"])` | `FileNotFoundError(2)` |
| `subprocess.run(["/data/service/hnp/bin/clang","--version"])` | `returncode 0` |
| `PATH=/data/service/hnp/bin` 后仍用裸名 | **仍然失败** ← 证明不是 PATH 内容问题 |

为什么故障面这么窄、极易误判：多数工具**自己**会先 which 解析（meson 对
`pkg-config`/`ninja` 就是这样，日志里打印的是绝对路径），只有**编译器探测那一步**
原样使用环境变量值 → 于是表现为"meson 找不到 clang"，看起来像"工具链没装"。

## 解决方案（推荐）

在 `conanfile.py` 的 `generate()` 里把所有工具链**解析成绝对路径**，env 与构建系统两条路径都覆盖：

```python
for env_var, exe in (("CC","clang"), ("CXX","clang++"), ("AR","llvm-ar"),
                     ("AS","llvm-as"), ("STRIP","llvm-strip"),
                     ("NM","llvm-nm"), ("RANLIB","llvm-ranlib")):
    path = shutil.which(exe)
    if not path:
        raise ConanException(f"{exe} not found in PATH — OHOS 工具链不可用")
    self.buildenv_info.define(env_var, path)       # 覆盖环境里的裸名

tc = MesonToolchain(self)
tc.binaries["c"]   = shutil.which("clang")          # 覆盖 native/cross 文件里的 bare name
tc.binaries["cpp"] = shutil.which("clang++")
tc.ar = shutil.which("llvm-ar"); tc.as_ = shutil.which("llvm-as")
tc.strip = shutil.which("llvm-strip")
tc.binaries["nm"] = shutil.which("llvm-nm"); tc.binaries["ranlib"] = shutil.which("llvm-ranlib")
```

要点：
- 用 `shutil.which()` 从 PATH 解析，**不要硬编码** `/data/service/hnp/bin`（跨机可移植）；
- 缺失即抛异常，**不要静默回退**（否则会退化成 R33 的"裸用未定义/无效工具导致静默失败"）；
- profile 的 `tools.build:compiler_executables` 只能覆盖 `c/cpp`，
  **`AR/AS/STRIP/NM/RANLIB` 仍来自 `AR` 等 env**，所以必须一并处理。

## 验证

```bash
$ CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
  AR=/data/service/hnp/bin/llvm-ar AS=/data/service/hnp/bin/llvm-as \
  STRIP=/data/service/hnp/bin/llvm-strip NM=/data/service/hnp/bin/llvm-nm \
  RANLIB=/data/service/hnp/bin/llvm-ranlib meson setup builddir src --buildtype=release
C compiler for the host machine: /data/service/hnp/bin/clang (clang 15.0.4 …)   # exit=0
```

修复后 `meson compile` 35/35 target 全绿，`conan create` exit=0。

## 反例（不要这么做）

- ❌ 去"安装 clang"/做软链 —— 文件一直都在，问题是查找机制；
- ❌ 只改 PATH 不改 CC —— PATH 本就有值，裸名问题依旧；
- ❌ 把 `CC` 改成相对路径或再包一层脚本 —— 仍需绝对路径才能真正被 spawn。

## 证据

- 首错现场：`archives/m/mmsd-tng/2.6.4/reports/00a-meson-setup.log`
- 修复后配置：`archives/m/mmsd-tng/2.6.4/reports/01-meson-compile-ohos.log`
- 适配笔记：`archives/m/mmsd-tng/2.6.4/notes.md` §2/E1（含 Python 侧最小复现）
