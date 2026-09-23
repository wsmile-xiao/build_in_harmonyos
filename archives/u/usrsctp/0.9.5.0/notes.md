# usrsctp 0.9.5.0 适配笔记

## 编译环境
- 构建系统: cmake（上游官方构建系统，usrsctplib 目标）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 下载官方 tag tarball（`https://github.com/sctplab/usrsctp/archive/refs/tags/0.9.5.0.tar.gz`，
   sha256=`260107ca...d62cd92`；本机 github 直连超时，用 codeload 可达源预置 tarball）
2. `cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
   -DCMAKE_C_FLAGS="-include $PWD/ohos_compat.h" \
   -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
   -Dsctp_debug=0 -Dsctp_werror=0 -Dsctp_build_shared_lib=0 -Dsctp_build_programs=1`
3. `cmake --build build -j2` → `build/usrsctplib/libusrsctp.a` 构建成功
4. 上游测试：`./test_timer`（退出码 0）、`./test_libmgmt`（退出码 0）
5. conan-init 生成配方 → 重写为 CMake 配方 + compat 头补丁 → conan-verify G0-G4 全过
6. finish（W2 结构 + R36 依赖 + W3 本地 CI 模拟）通过，状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `unknown type name 'u_int'/'u_long'/'u_short'` | E113: OHOS/musl 头文件缺 BSD 类型 | 创建 `ohos_compat.h`（`#if !defined(__FreeBSD__)&&!defined(__APPLE__)&&!defined(_WIN32)` 平台守卫），`CMAKE_C_FLAGS=-include` 注入 |
| 2 | `struct ifreq` 不完整类型（-std=c99 -pedantic） | musl 的 `struct ifreq` 完整定义与 timeradd/timercmp 宏受 `_GNU_SOURCE` 门控 | compat 头在包含任何系统头前 `#define _GNU_SOURCE 1` |
| 3 | CMake 4.1.2 报 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.0)` 过低 | 配方 generate() 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | 示例 `ekr_client`/`ekr_loop` 链接缺 `pthread_cancel` | OHOS libc 无该符号（nm -D libc.so 计数 0） | 平台限制，记录不阻塞；配方 `sctp_build_programs=0` 跳过可选示例 |

## 源码修改

补丁：`patches/0001-add-ohos-compat-header.patch`（新增 `ohos_compat.h`，72 行，
平台守卫为 `#if !defined(__FreeBSD__) && !defined(__APPLE__) && !defined(_WIN32)`，符合 E113 指引）

## 依赖版本

无第三方运行时依赖（仅系统 libc/pthread，W0 预检通过）。

## 验证结果

```bash
# 上游测试（实际运行）
$ ./test_timer          # 输出 Entering the loop / Exited the loop，退出码 0
$ ./test_libmgmt        # 退出码 0

# conan-verify（8 道门禁）
G0 预构建风险: PASS   G1 配方完整性: PASS   G2 conan create: PASS
G3 系统同名库隔离: PASS   G4 产物完整性: PASS
L2/L4/L5: 跳过（无 cache 路径）

# W3 本地 CI 模拟（finish Step5）
setup.sh: PASS   build_and_test.sh: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（compat 头注入 + CMake 4.x 策略兼容） |
| conandata.yml | 官方 tag tarball + sha256 + 补丁注册 |
| patches/0001-add-ohos-compat-header.patch | E113 compat 头 |
| test_package/ | 消费者测试（实质调用 usrsctp_init/socket/bind/close/finish，R34） |

## 注意事项

- compat 类型定义不能放在 `#if defined(__APPLE__)` 块内（OHOS 上 `__APPLE__` 未定义，整块被跳过）—— E113 第 4 条
- 本机 github.com 直连超时属网络环境限制，conan-verify 已用 E017 镜像注入完成干净构建验证

---
**编译结束**: 2026-09-08 02:32
**最终状态**: built
