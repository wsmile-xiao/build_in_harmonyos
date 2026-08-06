# iperf3 3.18 适配笔记

## 编译环境
- 构建系统: CMake (autotools config.status 在 HMDFS 上无法创建临时文件)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (Conan 配方已生成)

## 编译步骤
使用 CMake 构建（非 autotools）：
```bash
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_BUILD_TYPE=Release
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools config.status 失败 | HMDFS 文件系统限制：config.status 的 mktemp 创建目录后无法写入子文件 | 使用 CMake 替代 autotools 构建（补丁 0001 添加 CMakeLists.txt） |
| 2 | 平台识别 | config.guess/config.sub 不识别 HarmonyOS | 标准 autotools 补丁（保留以备 fallback） |
| 3 | pthread_cancel 等函数缺失 | HarmonyOS libc 不实现 pthread 取消函数 | 补丁 0002 提供 stub 实现 |
| 4 | Conan apply_conandata_patches 失败 | 新文件补丁使用 --- a/filename 格式，Conan 的 git apply 不支持 | conanfile.py 使用 patch -p1 手动应用补丁 |
| 5 | PACKAGE 宏重定义警告 | CMakeLists.txt 定义 PACKAGE="iperf3"，iperf_config.h 定义 PACKAGE="iperf" | 非致命警告，不影响功能 |

## 验证结果
```
iperf 3.18 (cJSON 1.7.15)
HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Tue Jun 23 02:15:22 UTC 2026 aarch64
Optional features available: CPU affinity setting, IPv6 flow label, TCP congestion algorithm setting, sendfile / zerocopy, socket pacing, bind to device, support IPv4 don't fragment, POSIX threads
```

## 补丁说明
- 7 个补丁涉及：CMakeLists.txt、pthread_stubs.c、iperf3.spec、config.guess、config.sub、iperf_config.h、version.h
- 补丁 0001 (CMakeLists.txt) 是核心适配：替换 autotools 为 CMake 构建系统
- 补丁 0002 (pthread_stubs.c) 提供 HarmonyOS 缺失的 pthread 取消函数

## Conan 适配
- package_type: application (命令行工具)
- 构建系统: CMake
- 无依赖（openssl 可选，未启用）
- test_package: 运行 iperf3 --version 验证二进制可用性
- 补丁应用: 手动使用 patch -p1（绕过 Conan apply_conandata_patches 的限制）

## 注意事项
- autotools 构建在 HarmonyOS 上因 config.status 临时文件权限问题无法使用
- CMake 构建正常，推荐使用
- iperf3 是命令行工具，不是库
---

**编译结束**: 2026-08-06 21:48
**最终状态**: built (Conan 适配完成)
**最后更新**: 2026-08-06T21:50:00 — submit PR
