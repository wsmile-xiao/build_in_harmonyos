# vgmplay 0.52.0：CMake install 清除 RUNPATH 会破坏 OHOS ELF 代码签名

- **草稿 ID**: `DRAFT-vgmplay-0.52.0-cmake-install-rpath-breaks-ohos-codesign`
- **来源**: `vgmplay/0.52.0` HarmonyOS PC 适配实战（frp-tip:56267 真机）
- **分类**: `cmake / conan / cli-tool / elf-signing / rpath / package()`
- **状态**: `VERIFIED DRAFT`，路径 B 知识库扩展候选，待审核
- **Issue/PR**: 本轮按任务要求不记录

## 适用场景

vgmplay 0.52.0 是基于 libvgm 的命令行 VGM 播放器（`package_type = "application"`，
产物为 `bin/vgmplay` ELF）。在 HarmonyOS PC（AArch64、musl、HMDFS、clang-15）
上适配时出现一个反直觉现象：

- **build 目录里的 `vgmplay` 能正常运行**（`--version` 输出 0.52.0）；
- **conan package 目录里的同名文件不能运行**，报
  `/system/bin/sh: .../p/bin/vgmplay: Operation not permitted`（exit 126）；
- 两个文件大小相同（1022464 字节），但 sha256 不同；
- 文件权限都是 `-rwxr-x---`，SELinux 上下文相同（`u:object_r:hmdfs:s0`），
  不是 Unix 权限或 SELinux 问题；
- `llvm-readobj -l` 对比 program headers 完全一致（LOAD/STACK/NOTE 段布局相同）；
- `llvm-readobj -n` 对比 notes 也一致（都有 `.note.ohos.ident`）。

这个组合症状——build 产物可执行、package 产物不可执行、ELF 表面结构正常——
适用于所有通过 Conan CMakeToolchain 构建、由 `cmake.install()` 打包、且工具链
自动注入 OHOS 代码签名的 application 包。

## 问题与错误签名

### 现象

conan create 编译成功，包已安装，但 test_package 执行：

```text
vgmplay/0.52.0 (test package): RUN: vgmplay --version | grep -q 'VGMPlay 0.52.0'
/system/bin/sh: /storage/.../p/bin/vgmplay: Operation not permitted
ERROR: vgmplay/0.52.0 (test package): Error in test() method
```

诊断过程中排除了以下常见原因：

1. **不是执行位**：`chmod 755` 无效，复制到 `/storage/.../tmp` 和
   `usr/local/bin` 都无效；
2. **不是 noexec 挂载**：同目录下 `hellocpp`、`ztest`（链接 libz.a）、
   `ltest`（链接 libvgm-utils.a）都能正常执行；
3. **不是静态链接问题**：手动用同样的 .o 文件 + 同样的静态库链接出的
   `myvgm` 能跑，输出 `VGMPlay 0.52.0`；
4. **不是 ELF 结构问题**：`llvm-readobj -h/-l/-n/-d` 对比 build 产物和
   package 产物，program headers、notes、NEEDED 库完全一致；
5. **不是 strip 问题**：`llvm-objcopy --strip-all` build 产物后确实不能跑，
   但 package 产物大小和 build 产物相同（都未 strip）。

### 根因

用 `llvm-readobj -d` 对比 build 产物和 package 产物的 dynamic section：

```text
# build 产物（能跑）
RUNPATH: [/storage/.../inih/lib:/storage/.../libvgm/lib:/storage/.../zlib/lib:]
NEEDED: libc++_shared.so
NEEDED: libc.so

# package 产物（不能跑）
NEEDED: libc++_shared.so
NEEDED: libc.so
# RUNPATH 消失了
```

CMake install(TARGETS) 时，Conan CMakeToolchain 默认设置
`CMAKE_INSTALL_RPATH` 为空（Conan 用 VirtualRunEnv 管理运行时库路径），
CMake 的 install 逻辑会**清除 ELF 的 DT_RUNPATH**。这个清除过程改写了
`.dynamic` 段的内容——而 OHOS clang wrapper（`/storage/.../clang++`）在链接时
自动传 `-Wl,--code-sign`，把代码签名数据嵌入了 ELF。**任何事后对 ELF
`.dynamic` 段的修改（清除/改写 RUNPATH）都会破坏签名数据，导致内核拒绝
execve**。

clang++ wrapper 脚本内容：

```sh
#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/clang-15" --driver-mode=g++ --sysroot="$DIR/../sysroot" \
  -fuse-ld=lld -Wl,--code-sign \
  -L"$DIR/../sysroot/usr/lib/aarch64-linux-ohos" -D__MUSL__ "$@"
```

关键：`-Wl,--code-sign` 在链接阶段生效，签名和 ELF 内容绑定。事后 patchelf、
chrpath、CMake install 的 rpath 清理、`llvm-objcopy --strip-all` 都会破坏绑定。

## 根因拆解

1. **签名绑定边界**：OHOS 的 `--code-sign` 不是独立的签名文件，而是把签名
   数据嵌入 ELF 本身。任何对 ELF 字节的事后修改（包括看似无害的 RUNPATH
   清除）都会使签名失效。
2. **Conan package 边界**：`cmake.install()` 不只是复制文件——CMake 的
   install(TARGETS) 在 install 阶段会根据 `CMAKE_INSTALL_RPATH` 重写 RUNPATH。
   当 `CMAKE_INSTALL_RPATH` 为空时，它清除 RUNPATH，触发签名破坏。
3. **build vs package 不可互换**：build 目录的 ELF 保留链接时的 RUNPATH
   和签名；package 目录的 ELF 被 CMake install 改写过。`conan create`
   的 test_package 用的是 package 目录，不是 build 目录。
4. **诊断信号**：如果 build 产物能跑但 package 产物不能跑、两者大小相同
   但 sha256 不同、且 `llvm-readobj -d` 发现 RUNPATH 消失，基本可以确认
   是 CMake install 的 rpath 清除破坏了 OHOS 签名。

## 推荐实现

### 1. package() 直接复制文件，不走 cmake.install()

对 `package_type = "application"` 且工具链自动 `--code-sign` 的包，不要在
`package()` 里调用 `cmake.install()`。改用 `conan.tools.files.copy` 直接从
build 目录复制最终 ELF 和数据文件，保持 ELF 字节不变：

```python
import os
from conan.tools.files import copy

def package(self):
    bin_dir = os.path.join(self.package_folder, "bin")
    # 直接复制 build 产物，CMake install 会清除 RUNPATH 并破坏 OHOS 签名
    copy(self, "vgmplay", src=self.build_folder, dst=bin_dir)
    # 数据文件（如有）
    for src_name, dst_name in [("Updates.txt", "updates.txt"), ...]:
        copy(self, src_name, src=self.source_folder, dst=bin_dir, keep_path=False)
        src = os.path.join(bin_dir, src_name)
        dst = os.path.join(bin_dir, dst_name)
        if os.path.exists(src):
            os.rename(src, dst)
```

### 2. 不要在 package() 里 strip 或 patchelf

同样的原则：不要对已签名的 ELF 做任何 `llvm-objcopy --strip-all`、`chrpath`、
`patchelf --remove-rpath` 操作。如果必须 strip（减小包体积），需要在
strip 后用 `binary-sign-tool` 重新签名（参考 cronutils 适配草稿）。

### 3. 诊断方法

遇到 "Operation not permitted" (exit 126) 时：

```sh
# 1. 确认 build 产物能跑
$BUILD_DIR/vgmplay --version

# 2. 对比 sha256（如果不同，说明 package 步骤修改了文件）
sha256sum $BUILD_DIR/vgmplay $PACKAGE_DIR/bin/vgmplay

# 3. 对比 RUNPATH（package 产物 RUNPATH 消失 = CMake install 破坏签名）
llvm-readobj -d $BUILD_DIR/vgmplay | grep -E "RUNPATH|NEEDED"
llvm-readobj -d $PACKAGE_DIR/bin/vgmplay | grep -E "RUNPATH|NEEDED"
```

### 4. test_package 必须实质运行二进制

`conan create` 的 test_package 运行的是 package 目录的二进制（不是 build
目录的），所以它能捕获这个签名破坏问题。空壳 test_package 或只检查文件
存在的测试会漏掉这个问题。

## 消费者验证

test_package 新增 6 条断言（全部在 frp-tip:56267 真机通过）：

1. `vgmplay --version` 含 `VGMPlay 0.52.0`
2. `vgmplay --version` 含 `supports VGM 1.72`
3. `vgmplay --lib-info` 含 `Supported formats`
4. `vgmplay --lib-info` 含 `- VGM`
5. `vgmplay --lib-info` 含 `YM2612`
6. `vgmplay --help` 含 `usage:`（消费者用例：验证 CLI 参数解析链路）

包 ref：`vgmplay/0.52.0#473784bd...:17da258aaaad...`（OHOS armv8 Release
clang15 libc++ cppstd17）。

## 与 cronutils 草稿的关系

cronutils 1.1 是 raw Makefile 构建，工具链**没有**自动 `--code-sign`，
需要在 package() 里手动 `binary-sign-tool sign`。

vgmplay 0.52.0 是 CMake 构建，clang wrapper **自动** `--code-sign`，但
CMake install 破坏了已签好的 ELF。两个草稿互补：

- 如果工具链不自动签名 → package() 里手动签名（cronutils 路径）；
- 如果工具链自动签名 → package() 里不要碰 ELF，直接 copy（vgmplay 路径）。
