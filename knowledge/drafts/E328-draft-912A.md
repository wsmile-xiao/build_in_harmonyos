# E328 草稿：为 Cargo 原生 CMake 子构建补全 OHOS SDK 缺失的 llvm-ranlib

> **状态**：`draft: true`
> **来源**：Stalwart CLI 1.0.5，知识库扩展 Issue #2237
> **验证对象**：`aws-lc-sys 0.39.1`，由 `reqwest 0.13.2` / rustls 依赖链引入

## 适用场景

适用于 Rust 软件通过 `build.rs` 和 Rust `cmake` crate 构建目标平台原生静态库的场景。此时存在两层构建配置：

1. Cargo/rustc 负责 `aarch64-unknown-linux-ohos` Rust 目标和最终 ELF；
2. 原生 crate 的 `build.rs` 另行启动 CMake，读取 OHOS SDK 的 `ohos.toolchain.cmake` 并生成 C/C++/汇编静态库。

只给 Cargo 设置 `AR_aarch64_unknown_linux_ohos` 并不保证子 CMake 使用同一归档索引工具，因为 CMake toolchain 会把工具路径写入自己的 cache。

## 真实错误链

### 1. 前置架构配置失败

首次调查只映射 Cargo linker、CC 和 AR。AWS-LC 的 CMake 子构建未获得完整 OHOS toolchain 配置，静态库中的 C 对象仍引用 AES/BN 汇编符号，但对应汇编对象未进入 archive，最终链接观察到：

```text
undefined reference to `aes_hw_encrypt`
undefined reference to `aes_hw_decrypt`
undefined reference to `bn_add_words`
```

这些符号不是 ranlib 缺失的特异性签名：已有 aws-lc 5.4.0 记录也表明，`CMAKE_SYSTEM_PROCESSOR=unknown` 会造成同类错误。诊断时必须同时检查 CMakeCache、`OHOS_ARCH` 和 archive 对象清单。`AWS_LC_SYS_EFFECTIVE_TARGET` 会影响绑定以及 OHOS 的部分目标/架构路由，但不能提供官方 toolchain 的 sysroot、编译器和完整平台配置，因此不能代替真正的 OHOS CMake toolchain。

### 2. 使用官方 OHOS CMake toolchain

在全新 Cargo target 目录中启用 aws-lc-sys 已提供的 OHOS NDK 通道后，正确的 `linux-aarch64` 预生成汇编源进入构建，但静态归档索引阶段失败。检查 SDK 和 CMake cache 得到：

```text
$ test -x "$OHOS_NDK_HOME/native/llvm/bin/llvm-ar" && echo llvm-ar-present
llvm-ar-present
$ test -e "$OHOS_NDK_HOME/native/llvm/bin/llvm-ranlib" || echo llvm-ranlib-missing
llvm-ranlib-missing

CMAKE_RANLIB:FILEPATH=<OHOS_NDK_HOME>/native/llvm/bin/llvm-ranlib
```

CMake 随后报告静态库 link/archive command 失败。根因不是“没有 LLVM 工具链”，而是官方 toolchain 已把一个不存在的 SDK 内路径固化到子构建 cache。

## 根因

OHOS SDK 提供 `llvm-ar`，但当前版本未提供同目录的独立 `llvm-ranlib`。LLVM 的 `llvm-ar s <archive>` 本身可生成或更新 archive symbol table，因此功能并非缺失；缺失的是 CMake toolchain 所期待的命令入口。

该问题跨越 Cargo 和 CMake 两层：

- `AR_aarch64_unknown_linux_ohos` 被 Cargo/cc crate 使用；
- `CMAKE_RANLIB`、`CMAKE_C_COMPILER_RANLIB` 和 `CMAKE_ASM_COMPILER_RANLIB` 由子 CMake 决定；
- 通用 `RANLIB` 环境变量无法覆盖已经由 toolchain 强制写入 cache 的绝对路径。

## 推荐方案

### 1. 生成构建目录内的 ranlib 包装器

```sh
cat > "$BUILD_DIR/llvm-ranlib" <<EOF
#!/bin/sh
exec "$LLVM_AR" s "\$@"
EOF
chmod +x "$BUILD_DIR/llvm-ranlib"
```

包装器必须位于 Conan/Cargo 构建目录，不能写入或修改共享 SDK。

### 2. 生成薄 CMake toolchain overlay

以下内容中的 `<OHOS_TOOLCHAIN_ABS>` 和 `<RANLIB_WRAPPER_ABS>` 必须由配方在生成文件时替换为经过校验和 CMake 字符串转义的绝对路径，不能把 shell 变量名原样写进 CMake：

```cmake
include("<OHOS_TOOLCHAIN_ABS>")
set(CMAKE_RANLIB "<RANLIB_WRAPPER_ABS>" CACHE FILEPATH "" FORCE)
set(CMAKE_C_COMPILER_RANLIB "<RANLIB_WRAPPER_ABS>" CACHE FILEPATH "" FORCE)
set(CMAKE_ASM_COMPILER_RANLIB "<RANLIB_WRAPPER_ABS>" CACHE FILEPATH "" FORCE)
```

也可在 CMake 中用 `$ENV{OHOS_NDK_HOME}` 读取环境变量，但包装器路径仍需通过明确的 `-D` 变量传入。路径中的反斜杠、双引号和分号必须安全转义。必须先 include 官方 toolchain，保留 OHOS target、sysroot、编译器和架构汇编源选择，再只覆盖缺失的 ranlib 入口。

### 3. 通过 crate 的 target-specific hook 注入

aws-lc-sys 提供目标限定的 CMake toolchain 环境变量：

```sh
export AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos="$BUILD_DIR/aws-lc-ohos-toolchain.cmake"
cargo build --release --locked
```

使用目标限定变量可避免覆盖 build-context 或其他架构的 CMake 子构建。其他 Rust 原生 crate 若提供不同的 toolchain hook，应映射到其实际接口，不能照搬变量名。

## Conan 配方映射

配方从 `tools.build:compiler_executables` 获取 clang/llvm-ar，并优先从 `OHOS_NDK_HOME` 获取官方 toolchain。若环境没有显式 NDK 路径，才在解析 `which`/绝对 linker 后尝试 SDK 邻接布局；两种方式都必须检查 `ohos.toolchain.cmake` 真实存在，否则 fail closed。

包装器、overlay 和 `CARGO_TARGET_DIR` 都位于 `self.build_folder`，不写 Cargo registry、SDK、源码目录或用户全局配置。

## 验证

```sh
# 1. 证明 SDK 路径缺口
ls -l "$OHOS_NDK_HOME/native/llvm/bin/llvm-ar"
test ! -e "$OHOS_NDK_HOME/native/llvm/bin/llvm-ranlib"

# 2. 干净构建，避免旧 CMake cache 造成假阳性
rm -rf <cargo-target>
CARGO_TARGET_DIR=<cargo-target> cargo build --release --locked
CARGO_TARGET_DIR=<cargo-target> cargo test --release --locked -- --nocapture

# 3. 在干净构建后证明新 CMake cache 使用构建目录内的包装器
grep -E '^CMAKE_(RANLIB|C_COMPILER_RANLIB|ASM_COMPILER_RANLIB):.*<build-local-wrapper>' \
  <cargo-target>/release/build/aws-lc-sys-*/out/build/CMakeCache.txt

# 4. 核验同一干净 target 目录内的最终目标
file <cargo-target>/release/stalwart-cli
readelf -h <cargo-target>/release/stalwart-cli
readelf -l <cargo-target>/release/stalwart-cli | grep 'Requesting program interpreter'
```

Stalwart CLI 1.0.5 的干净 Conan 构建结果：

- 最终产物为 AArch64 OHOS ELF，解释器为 `/lib/ld-musl-aarch64.so.1`；
- 上游 75 个单元测试真实通过；
- 13 个依赖完整 localhost Stalwart 服务端的集成函数提前返回，按 skipped 而非 passed 统计；
- 打包后的消费者通过 localhost-only mock JMAP 服务完成 9/9 断言；
- W3 本地 CI 模拟和第三轮 W4 独立审计通过。

## 查重与新增边界

| 已有知识 | 已覆盖内容 | 本草稿新增内容 |
|---|---|---|
| E012 | 使用 LLVM `ar`/`ranlib` 替代 GNU binutils | SDK 没有独立 `llvm-ranlib`，且 OHOS CMake toolchain 已把缺失绝对路径写入子构建 cache；需要 `llvm-ar s` 包装器和 target-scoped overlay |
| E267 | `CMAKE_SYSTEM_NAME` 的 OHOS/HarmonyOS/Linux 平台识别 | 不改变系统名；保留官方 OHOS toolchain，仅覆盖缺失的归档索引工具 |
| E296 | Windows 构建机上补全 Meson cross file 的 `llvm-ar.exe`/`llvm-ranlib.exe` | Linux/OHOS 原生环境、Cargo build.rs 启动的嵌套 CMake，以及 SDK 实际缺少 ranlib 入口 |
| E327 草稿 | Conan build/host 编译器到自定义 HOSTCC/HOSTLD 的双上下文映射 | 目标 Rust crate 内部 CMake cache 与缺失 SDK 工具入口，不涉及构建机生成器执行 |

因此本草稿不重复申报“应使用 LLVM 工具链”，新增点是：**当 SDK CMake toolchain 指向不存在的 ranlib 时，如何在不修改 SDK、不伪装 Linux target 的前提下，为 Cargo 原生子构建提供目标限定、可复现的 archive-index 工具闭包。**

## 禁止做法

- 禁止在 release 构建中设置 `AWS_LC_SYS_NO_ASM=1`；上游会拒绝，且改变正式产物路径。
- 禁止把 `llvm-ar` 复制、重命名或链接到共享 SDK 的 `llvm-ranlib` 路径；这会污染工具链并让 CI 不可复现。
- 禁止用 `CMAKE_SYSTEM_NAME=Linux` 或 Linux Rust target 冒充 OHOS 构建成功。
- 禁止只复用旧 Cargo target/CMake cache验证修复；必须删除 target 目录做干净构建。
- 禁止把 Cargo 编译成功、13 个提前返回的集成函数或 `--help` 输出计为核心测试通过。

## 适用边界

若 SDK 后续正式提供可执行的 `native/llvm/bin/llvm-ranlib`，应优先使用官方工具并移除 overlay。若原生 crate 不使用 CMake，或其构建系统不会读取 `CMAKE_RANLIB`，则应按实际子构建接口映射，不能套用本方案。
