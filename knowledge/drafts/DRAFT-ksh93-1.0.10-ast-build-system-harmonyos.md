# DRAFT-ksh93-1.0.10-ast-build-system-harmonyos — HarmonyOS 下 AT&T AST bin/package 构建系统适配

## 错误特征

HarmonyOS 环境下构建使用 AT&T AST `bin/package` 构建系统的软件（如 ksh93）时，遇到以下典型失败：

**构建阶段**（`bin/package` 脚本 stderr）：

    mkfifo: <build>/arch/<hosttype>/lib/package/gen/make.out.fifo: Operation not permitted
    package: make done at ... in <build>/arch/<hosttype>

随后 Conan 捕获非零退出码并中止：

    ERROR: ksh93/1.0.10@ohpcd/stable: Error in build() method, line 22
    ConanException: Error 1 while executing

**链接阶段**（未设 AST_NO_DYLIB 时，`mamake` 输出）：

    ln: cannot create symbolic link from 'libast.so.6.0' to '.../dyn/lib/libast.so.6': Permission denied
    mamake [lib/libast]: *** exit code 1 making .../dyn/lib/libast.so

**运行时**（测试阶段）：

    panic: process substitution: FIFO creation failed [Operation not permitted]

**复现命令**：

    conan create archives/k/ksh93/1.0.10 \
      --user=ohpcd --channel=stable \
      -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
      -pr:b=$HOME/.conan2/profiles/ohos-aarch64

## 触发条件

- 构建系统: AT&T AST `bin/package`（基于 Mamfile，非 Meson/CMake/Autotools）
- 阶段: build（默认 `make` 模式 + 动态库链接）、testing（进程替换测试）
- 典型库: ksh93、ast-open 系列工具

## 根因分析

1. **HMDFS 禁止 mkfifo(2)**：`bin/package` 在默认（非 quiet）模式下调用 `mkfifo -m 600 $o.fifo` 创建命名管道，用于 `tee` 同时输出到终端和 `make.out`。HarmonyOS 的 HMDFS 文件系统禁止用户进程创建 FIFO，返回 `Operation not permitted`。ksh93 的进程替换 `<()` / `>()` 同样依赖 FIFO，在运行时测试中也失败。

2. **HarmonyOS 禁止第三方应用创建符号链接**：AST 构建系统在链接动态库（`libast.so`）后创建 `libast.so.6`、`libast.so` 等版本化符号链接，调用 `symlink(2)` 返回 `EACCES`。`bracket`、`glob` 等测试模块也因 `ln -s` 失败。

3. **用户 ID 映射差异**：HarmonyOS 用户 ID 映射与标准 Linux 不同（`id: bad uid 20020100`），导致文件权限测试 `-r` / `-w` / `-O` 判断异常。

## 解决方案

### 推荐方案

1. **构建命令**：使用 `bin/package quiet make` 替代 `bin/package make`。`quiet=1` 时走 `cmd="$cmd >> $o"` 分支，不创建 FIFO。
2. **跳过动态库**：设置 `AST_NO_DYLIB=y`，只编译静态链接版本，避免 `symlink(2)` 调用。上游 README 明确支持该变量。
3. **conanfile.py**：

    def build(self):
        ccflags = "-O2 -fPIC"
        ldflags = ""
        self.run(
            f'AST_NO_DYLIB=y bash bin/package quiet make '
            f'CCFLAGS="{ccflags}" LDFLAGS="{ldflags}"'
        )

4. **test_package**：消费者测试验证 `ksh` 在无 `/bin/bash` 环境下可运行，检查可执行权限、`SHELL` 路径存在性，`shcomp --help` 用 `ignore_errors=True`（AT&T 工具用 exit 2 表示帮助）。

### 回退方案

若无法使用 quiet 模式，可对 `bin/package` 打补丁，将 `mkfifo -m 600 $o.fifo || exit` 替换为 `true`，并配合 `MAKEFLAGS=-j1` 强制单线程。

## 实际验证结果

- `conan create`：构建成功，产出静态链接的 `ksh`、`shcomp`。
- 消费者测试：6 项全部通过（基础功能、算术运算、无 `/bin/bash` 环境、可执行权限、`SHELL` 路径、`shcomp`）。
- 上游回归测试（`bin/package quiet test`）：
    - 总测试用例数：14287
    - 通过：13495
    - 失败：792
    - 通过率：94.5%
- 失败模块及原因（均为平台限制，非适配问题）：
    - `alias` / `basic` / `sh_match`：进程替换依赖 FIFO
    - `bracket` / `glob`：符号链接创建失败
    - `builtins` / `io` / `libcmd` / `path` / `subshell`：综合平台限制
    - `coprocess` / `options` / `posix` / `restricted` / `signal` / `tilde`：信号/权限/协进程相关

## 禁止做法

- ❌ 禁止硬编码 `LD_LIBRARY_PATH=.../.conan2/p/...` 修补运行环境，必须由 VirtualRunEnv 生成
- ❌ 禁止通过 LD_PRELOAD 或修改系统调用绕过 HMDFS 的 FIFO 限制
- ❌ 禁止写"上游无测试用例"（ksh93 有 14287 个测试）
- ❌ 禁止写 100% 通过率（实际 94.5%，失败均为平台限制）
- ❌ 禁止将平台限制导致的失败归因于适配 bug

## 验证

构建：

    conan create archives/k/ksh93/1.0.10 \
      --user=ohpcd --channel=stable \
      -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
      -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing

上游测试（在构建目录手动运行）：

    cd <build_folder>
    export SHELL="$(pwd)/arch/linux.arm64-64/bin/ksh"
    export SHCOMP="$(pwd)/arch/linux.arm64-64/bin/shcomp"
    bash bin/package quiet test
    # 预期：14287 tests, 13495 passed, 792 errors（94.5%）

## 关联条目

- 相关: E011（OHOS 上运行 Linux 文件系统镜像类上游测试的兼容性处理）
