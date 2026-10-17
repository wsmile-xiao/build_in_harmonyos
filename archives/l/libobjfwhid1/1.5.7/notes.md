# libobjfwhid1 1.5.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang 15 (Objective-C) / clang++
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64), OS=OHOS 6.0, HongMeng Kernel 1.12.0
- 状态: built（conan-verify 通过，未 upload）

## 背景
- 上游: ObjFW (https://objfw.nil.im/) 整体源码树，Autotools 构建。
  一次构建产出 libobjfw、libobjfwrt、libobjfwhid 等库。
- 本包名 libobjfwhid1，聚焦 HID/手柄库 libobjfwhid（Linux 后端用 evdev）。
- 无外部 conan 依赖（无需 libusb/hidapi），配方自包含。

## 编译步骤

### 探索阶段（模式 B）
```bash
# 1. 平台识别打补丁（config.guess/config.sub，E007 规程）
perl scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub
#   - config.guess: __OHOS__ LIBC 检测 + HarmonyOS 系统识别 → aarch64-unknown-linux-ohos
#   - config.sub: ohos-linux triplet + ohos* OS 列表

# 2. 补充 config.sub kernel-OS 校验表（patch-autotools-ohos.pl 在此新版 config.sub 未命中，E122/E268）：
#    在 "linux-gnu*- | ... | linux-mlibc*- )" 行追加 "| linux-ohos*- "
#    否则报 "Kernel 'linux' not known to work with OS 'ohos'"

# 3. configure（--without-tls：OHOS 无可用 TLS 后端，HID 也不需要）
source .build-context-libobjfwhid1-1.5.7
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --without-tls

# 4. make
make -j8

# 5. make check（上游测试，见「验证结果」）
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config.guess 无 __OHOS__/HarmonyOS 分支 (E007) | patch-autotools-ohos.pl |
| 2 | config.sub 报 Kernel 'linux' not known to work with OS 'ohos' | 新版 config.sub 的 kernel-OS 校验表 (linux-gnu*-...linux-mlibc*-) 未含 linux-ohos（脚本未命中，E122/E268） | 手动追加 linux-ohos*- 到该校验表 |
| 3 | configure 临时目录不可写（umask 077） | HMDFS UID 映射 + umask 077 (E011) | configure umask 077→022 |
| 4 | TLS 后端无法构建 | OHOS 无 OpenSSL/GnuTLS/mbedTLS 后端可用 | configure --without-tls（HID 不依赖 TLS） |

## 源码修改

探索阶段源码修改（R3，未生成 .patch，finish 时由 refresh-patch --auto 固化）：
- build-aux/config.guess：__OHOS__ LIBC 检测 + HarmonyOS 系统识别（patch-autotools-ohos.pl 自动）
- build-aux/config.sub：ohos-linux triplet + ohos* OS 列表（patch-autotools-ohos.pl 自动）
- build-aux/config.sub：kernel-OS 校验表追加 linux-ohos*-（手工，脚本未命中，E122/E268）
- configure：umask 077→022（E011）

## 验证结果

### 上游测试（make check）
```bash
cd $BUILD_SRC_DIR
make check
```
- **结果: 1238 通过 / 0 失败 / 4 跳过**（exit code 0，2026-09-16 实测）
- 跳过项（4，均为平台能力缺失，非库缺陷）：
  - `-[OFUNIXStreamSocketTests testUNIXStreamSocket]` — UNIX stream sockets unsupported
  - `-[OFUNIXDatagramSocketTests testUNIXDatagramSocket]` — UNIX datagram sockets unsupported
  - `-[OFUNIXSequencedPacketSocketTests testUNIXSequencedSocket]` — UNIX sequenced packet sockets unsupported
  - `-[OFFileManagerTests testLinkItemAtPathToPath]` — Links not supported
- 注意：任务描述中探索记录为 1239 通过，本次独立复核 `make check` 实测为 **1238 通过**（差 1，可能为探索时构建状态差异或转写误差；以本次实测 1238 为准）。

### 消费者测试（test_package）
- conan create 自动编译 test_package：Objective-C 消费者真实调用
  `+[OHGameController controllers]`（ObjFWHID 公开 API，evdev 后端），
  链接 libobjfwhid / libobjfw / libobjfwrt。
- 沙箱/CI 无 /dev/input 设备权限时，后端抛 OFOpenItemFailedException，
  test.m 按预期平台限制捕获并输出 "libobjfwhid OK (device enumeration unavailable...)"，exit 0。

### 链接验证（探索阶段）
- static（--disable-shared --enable-static）与 shared（默认双产物）两条路径均可链接通过。

## 产物说明

conan create 产出（package 目录，剔除 bin/sbin 使包保持纯库类型，R38）：
- include/ObjFWHID/ 与 include/ObjFW/ 等头文件
- lib/libobjfwhid.{a,so} / lib/libobjfw.{a,so} / lib/libobjfwrt.{a,so}
  （及 libobjfwrt.so 的 ObjFW 运行时）
- 配方 cpp_info.libs = ["objfwhid", "objfw", "objfwrt"]

## 注意事项

- ObjFW 是 Objective-C 库，需要 clang 的 ObjC 支持（clang 15 内置）。
- 消费者编译需 ObjFW 运行时 flags（`-fconstant-string-class=OFConstantString`、
  `-Xclang -fobjc-runtime=objfw-1.5`），见 test_package/CMakeLists.txt。
- make check 的 4 个跳过项均为平台能力缺失（UNIX socket/硬链接），与 E046 (chmod)、
  E051 (未实现 syscall)、E002 (/tmp 只读) 同属鸿蒙运行期限制，非库缺陷。
- **in-source 构建**：ObjFW 的 Makefile 为 tarball 静态文件（非 automake 生成），
  conan 配方必须 `folders.build = "."`（in-source），否则 out-of-tree 无 Makefile。
- **make -j1**：HMDFS 上 make -jN 的 jobserver mkfifo（TMPDIR）报 Operation not
  permitted（E074），配方统一用 -j1（探索阶段 work 目录用 -j8 可过，conan 内改为 -j1）。
---

**编译结束**: 2026-09-16 16:13
**最终状态**: built
