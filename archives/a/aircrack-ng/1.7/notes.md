# aircrack-ng 1.7 编译笔记

## 编译状态：built（成功）

### 源代码获取
- 来源：https://download.aircrack-ng.org/aircrack-ng-1.7.tar.gz
- 大小：7740634 bytes
- 日期：2022-05-11

### 编译环境
- 平台：HarmonyOS aarch64
- 编译器：clang 15.0.4
- 依赖：openssl/3.5.6, zlib/1.3.1
- 构建工具：automake/1.18, libtool/2.5.4 (via Conan tool_requires)

### 编译过程

#### 1. Conan 配方架构
- 使用 tool_requires("automake/1.18") 和 tool_requires("libtool/2.5.4") 提供构建工具
- 无硬编码路径（R33 合规）
- pkg.m4 通过 shutil.which("pkg-config") 动态发现，设置 ACLOCAL_PATH

#### 2. Autotools 重生成
- 源码包仅包含 configure.ac，无预生成 configure
- 运行 autoreconf -fiv 生成 configure 脚本
- Autoconf 生成的 configure/config.status 默认使用 ./confXXXXXX 和 umask 077
  创建临时文件，在 HMDFS 上失败
- 构建脚本 post-autoreconf 将 ./confXXXXXX 替换为 ${TMPDIR:-/tmp}/confXXXXXX
  并移除 umask 077，作为 HMDFS 平台适配（autoconf 模板无法通过 configure.ac 修改）

#### 3. 平台适配
- sockaddr_storage 重复定义：使用 _UAPI_LINUX_SOCKET_H 守卫（POSIX 兼容，无 #ifdef __OHOS__）
- 补丁 0001: lib/osdep/linux.c
- 补丁 0002: lib/osdep/linux_tap.c

#### 4. OpenSSL 适配
- 使用 openssl/3.5.6（非 EOL 版本）
- -Wno-deprecated-declarations 处理废弃 API 警告
- SHA1_Init/Update/Final 等 API 在 OpenSSL 3.x 中标记为废弃但可用

### 配置选项
- --enable-static: 静态构建
- --disable-shared: 禁用共享库
- --with-libnl=no: 禁用 libnl（HarmonyOS 不支持）
- -Wno-deprecated-declarations: 忽略 OpenSSL 3.x 废弃 API 警告

### 测试包
- test.c 验证 version.h 中版本宏（_MAJ, _MIN, _SUB_MIN）
- test_package 通过 conanrun 环境运行编译后的测试
- 同时运行 aircrack-ng --help 验证二进制可执行

### 已编译工具
aircrack-ng, airbase-ng, aireplay-ng, airodump-ng, airmon-ng,
airolib-ng, airserv-ng, airtun-ng, besside-ng, easside-ng,
ivstools, kstats, makeivs-ng, packetforge-ng

### 编译知识点

1. **tool_requires 替代硬编码路径**
   - automake/1.18 和 libtool/2.5.4 通过 Conan 管理
   - 自动设置 PATH 和环境变量
   - 满足 R33 规则

2. **HMDFS 临时文件适配**
   - Autoconf 生成的 configure 使用 ./confXXXXXX 和 umask 077
   - 在 HMDFS 上 umask 077 导致 Permission denied
   - 构建脚本将 ./ 替换为 ${TMPDIR:-/tmp}/ 并移除 umask 077
   - 这是 autoconf 内部模板的行为，无法通过 configure.ac 修改

3. **pkg.m4 动态发现**
   - 通过 shutil.which("pkg-config") 定位 pkg-config
   - 解析符号链接获取真实路径
   - 设置 ACLOCAL_PATH 环境变量

4. **POSIX 兼容的平台适配**
   - 使用 #if !defined(_UAPI_LINUX_SOCKET_H) 而非 #ifdef __OHOS__
   - 满足 R8 规则

---
**编译结束**：2026-08-09
**最终状态**：built（全部工具编译成功）
---

**编译结束**: 2026-08-09 04:20
**最终状态**: built
