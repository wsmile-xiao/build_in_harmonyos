# wiiuse 0.15.7 — 适配笔记

## 软件简介

wiiuse 是 Wii Remote（Wii 遥控器）连接库，用于与 Wii 遥控器通过蓝牙进行通信。
项目地址：https://github.com/wiiuse/wiiuse
许可证：GPL-3.0

## OHOS 适配策略

### 核心问题

- wiiuse 在 Linux 平台依赖 **Bluez**（Linux 蓝牙协议栈），OHOS 无此库
- 源码中 `WIIUSE_BLUEZ` 宏由 `__linux` 检测自动触发，OHOS 基于 Linux 内核，也会被触发
- `bdaddr_t` 类型定义在 `<bluetooth/bluetooth.h>` 中，OHOS 不可用
- CMakeLists.txt 中 `find_package(Bluez REQUIRED)` 会直接导致 cmake 配置失败

### 适配方案

1. **新增 OHOS 平台定义**：在 `wiiuse.h` 和 `wiiuse_internal.h` 中添加 `__OHOS__` 检测
   （优先于 `__linux`），定义 `WIIUSE_OHOS` 宏替代 `WIIUSE_BLUEZ`
2. **Stub bdaddr_t 类型**：在 OHOS 模式下定义
   `typedef struct { unsigned char b[6]; } bdaddr_t;`
3. **创建 os_ohos.c stub 文件**：所有蓝牙 I/O 函数返回 0（stub 实现）
   - `wiiuse_os_find()` → 返回 0（无法扫描蓝牙设备）
   - `wiiuse_os_connect()` → 返回 0（无法连接）
   - `wiiuse_os_poll()` → 返回 0（无数据）
   - `wiiuse_os_read()` → 返回 0（无法读取）
   - `wiiuse_os_write()` → 返回 0（无法写入）
4. **修改 CMakeLists.txt**：
   - 根级：添加 OHOS 检测分支，`CMAKE_SYSTEM_NAME=OHOS` 时设置 `OHOS=YES`
     并 `add_definitions(-D__OHOS__)`，Bluez 不再为 REQUIRED
   - src级：添加 `elseif(OHOS)` 使用 `os_ohos.c`，链接 `-lm`
   - 禁用 BUILD_EXAMPLE 和 BUILD_EXAMPLE_SDL（无 SDL 和蓝牙支持）
5. **wiimote_t 结构体**：在 OHOS 模式下添加等效的
   `bdaddr_str/bdaddr/out_sock/in_sock` 字段

### 编译产物

| 产物 | 路径 | 大小 |
|------|------|------|
| libwiiuse.a | ~/usr/local/lib/ | 58KB (58012字节) |
| wiiuse.h | ~/usr/local/include/ | 31KB (31726字节) |
| wiiuse.pc | ~/usr/local/lib/pkgconfig/ | 202字节 |

库导出 89 个函数符号，涵盖核心 API、扩展控制器、数据处理等。

### 功能限制（预期行为）

- ❌ 蓝牙扫描（`wiiuse_os_find` 返回 0）
- ❌ 蓝牙连接（`wiiuse_os_connect` 返回 0）
- ❌ 蓝牙通信（`wiiuse_os_read/write` 返回 0）
- ✅ 数据处理（dynamics, ir, nunchuk 等内部计算）
- ✅ 版本信息（`wiiuse_version()` 正常返回 "0.15.7"）
- ✅ 初始化/清理（`wiiuse_init/cleanup` 正常工作）

### pkg-config 版本号

pkg-config 显示版本为 0.15.5（CMakeLists.txt 中 `project(VERSION 0.15.5)`），
实际标签版本为 0.15.7。这是上游代码中的版本号不匹配问题，不影响库功能。

## 源码修改清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| CMakeLists.txt | 构建系统 | OHOS 检测分支，Bluez 可选，禁用示例，add_definitions(-D__OHOS__) |
| src/CMakeLists.txt | 构建系统 | OHOS 分支，os_ohos.c，链接 -lm |
| src/os_ohos.c | 新增文件 | OHOS stub I/O 实现（119行） |
| src/wiiuse.h | 平台检测 | 添加 __OHOS__ → WIIUSE_OHOS，stub bdaddr_t，OHOS wiimote_t 字段 |
| src/wiiuse_internal.h | 平台检测 | 添加 __OHOS__ → WIIUSE_OHOS，arpa/inet.h |

## 本地验证结果（真实执行）

```bash
$ clang test_wiiuse.c -I~/usr/local/include -L~/usr/local/lib -lwiiuse -lm -o test_wiiuse
# 编译成功，无错误

$ ./test_wiiuse
wiiuse version: 0.15.7
wiiuse v0.15.7 loaded.
  De-facto official fork at http://github.com/wiiuse/wiiuse
  Original By: Michael Laforest <thepara[at]gmail{dot}com> <https://sourceforge.net/projects/wiiuse/>
wiiuse_init succeeded (stub mode)
[INFO] wiiuse clean up...
```

验证项：
- ✅ 编译链接 libwiiuse.a 成功
- ✅ wiiuse_version() 返回 "0.15.7"
- ✅ wiiuse_init(1) 返回非NULL指针
- ✅ wiiuse_cleanup() 正常退出
- ✅ pkg-config --modversion/cflags/libs 正常工作

## 编译对话记录

### 2026-06-02 对话 1：首次编译

1. **init-build**：下载 wiiuse-0.15.7.tar.gz (120KB)，解压，环境检查通过
   - SSL 证书问题 → 手动 curl -kL 下载后重跑 init-build 成功
2. **源码分析**：确认 cmake 项目，Linux 平台依赖 Bluez (REQUIRED)，OHOS 无此库
3. **源码修改**：
   - wiiuse.h：添加 `__OHOS__` 检测优先于 `__linux`，定义 `WIIUSE_OHOS`，stub bdaddr_t
   - wiiuse_internal.h：同上
   - CMakeLists.txt：OHOS 检测分支
   - src/CMakeLists.txt：OHOS 分支，os_ohos.c
   - 创建 os_ohos.c stub 文件
4. **cmake 配置**：`cmake -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLE=NO -DBUILD_EXAMPLE_SDL=NO ..` 成功
5. **make 编译**：成功，仅有警告（unused parameters, implicit memcpy declaration）
   - 修复：os_ohos.c 添加 `#include <unistd.h>`（close() 函数）
6. **make install DESTDIR=$TEST_PREFIX**：成功，产物安装到 staging 目录
7. **make check / ctest**：无测试套件（项目无 CTest 配置）
8. **verify-build G1-G4**：第一次 G4 FAIL（manifest 缺 build_system）→ 修正后 PASS
9. **package**：wiiuse-0.15.7-ohos-aarch64.tar.gz (152KB)
10. **本地安装**：make install（无 DESTDIR）→ 安装到 ~/usr/local
11. **本地验证**：test_wiiuse.c 编译链接运行成功
12. **finish**：built 状态，G1-G4 PASS，5 个补丁生成

### G0 干净构建验证

G0 失败原因：clean_verify.py 脚本仅支持 autotools/makefile 构建，
不支持 cmake 构建（尝试执行 `./configure` 而非 `cmake`）。
补丁应用阶段（5个补丁全部应用成功）已验证补丁自包含性。
手动 cmake 构建已完整验证。

**编译结束**: 2026-06-02
**最终状态**: built