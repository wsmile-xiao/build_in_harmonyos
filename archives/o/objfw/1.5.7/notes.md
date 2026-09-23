# objfw 1.5.7 适配笔记

## 概述
ObjFW 是 Objective-C 语言的便携框架（runtime + 标准库），自带 ObjC runtime，
不依赖 GNUstep/libobjc2。构建系统为自定义 buildsys（configure 脚本 + buildsys.mk，非 autotools automake）。

## 关键路径

### 1. 源码选择
- 上游 GitHub 仓库（git tag 1.5.7-release）**不含预生成 configure**（需 aclocal+autoconf 生成，CI 缺 aclocal）
- **官方 release tarball**（https://objfw.nil.im/downloads/objfw-1.5.7.tar.gz）带预生成 configure，选此源
- sha256: e637c32731dc07396b812c4019f34d1417a3f7aa39d450b7f27c9bcdc23b3e12

### 2. 补丁（2 个）
1. `0001-config.sub-ohos.patch`：config.sub 增加 ohos 识别（linux-ohos kernel-os 校验 + ohos OS 列表），使 --host=aarch64-linux-ohos 通过
2. `0002-configure-hmdfs-umask.patch`：configure 临时目录 umask 077→022（E011，HMDFS 上 mktemp 创建 0700+setgid 目录 owner 为 file_manager(1006) 导致写 Permission denied）

### 3. 编译器
- ObjC 编译用 clang `-fobjc-runtime=objfw`（configure 自动探测）
- OHOS clang 15.0.4 完整支持 ObjC + blocks（configure 检查全过）
- AC_PROG_OBJC 需 OBJC=clang 环境变量（configure 探测 clang/gcc 均可）

### 4. 依赖
- openssl/3.5.6（TLS，--with-tls 默认开；也可 --without-tls 关闭）
- zlib/1.3.1（GZIP 流）
- 通过 CPPFLAGS/LDFLAGS 注入 Conan 包路径

### 5. 交叉编译
- `--host=aarch64-linux-ohos --build=aarch64-unknown-linux-ohos`（config.sub 补丁后识别）
- 警告 "using cross tools not prefixed with host triplet" 无害

### 6. 平台排查点结论
- **asm 段**：src/runtime/lookup-asm 有 arm64-elf 实现，正常编译链接
- **TLS**：configure 探测 OHOS musl TLS 可用（默认开启）
- **信号处理**：make check 全绿，无信号相关问题
- **make -j1**：HMDFS mkfifo jobserver 限制

### 7. 测试
- make check：**1243 tests succeeded, 0 failed, 0 skipped**（本机 HarmonyOS PC arm64 实跑）

## 产物
- libobjfw.so（主框架）、libobjfwrt.so（runtime）、libobjfwtls.so（TLS 桥）
- libobjfwhid.so（HID，+libobjfwtest.a 测试库）
- 工具：objfw-config、objfw-compile、objfw-embed、objfw-new、ofarc、ofdns、ofhash、ofhttp 等
- cmake 配置：lib/cmake/ObjFW/

## 已知问题
- HMDFS 源码目录构建会因 umask 077 临时目录权限失败（见补丁 2）；本地 conan 构建需 CONAN_HOME 指向 /data 分区（el2/base/temp），CI 无此问题
