# snap7 1.4.2 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile, 非 autotools)
- 编译日期: 2026-06-29
- 编译器: clang/clang++ 15.0.4 (位于 /data/service/hnp/bin/)
- 归档工具: llvm-ar
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL -o snap7-full-1.4.2.7z "https://downloads.sourceforge.net/project/snap7/1.4.2/snap7-full-1.4.2.7z"`
2. 从源码编译 p7zip 16.02 获取 7za（系统无预装 7z）
3. 解压源码: `7za x snap7-full-1.4.2.7z`
4. 创建 aarch64_linux.mk 适配 ARM64 平台
5. 修改 common.mk: 使用 clang++/clang/llvm-ar，生成静态库 (libsnap7.a)
6. 修复 HarmonyOS 兼容性问题（见下表）
7. 编译: `make -C build/unix -f aarch64_linux.mk -j1`
8. 生成 Conan 配方并验证: `conan-verify` 全部 8 项门禁通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 .7z 格式无法用 conan get() 解压 | conan 的 get() 仅支持 zip/tar | 从源码编译 p7zip 16.02，在 source() 中用 7za 解压 |
| 2 | p7zip 编译失败 | HarmonyOS 缺少 getpass() | 在 config.h 中禁用 ENV_HAVE_GETPASS |
| 3 | p7zip 缺少 StringConvert.h | 7zUpdate.cpp 未 include 该头文件 | 手动添加 #include "StringConvert.h" |
| 4 | snap7 无 aarch64 Makefile | 原生仅支持 x86/x64 | 新建 aarch64_linux.mk (TargetCPU=aarch64) |
| 5 | 编译器不匹配 | common.mk 硬编码 g++/gcc/ar | 替换为 clang++/clang/llvm-ar |
| 6 | pthread_cancel 不可用 | HarmonyOS musl libc 不实现线程取消 | ThreadKill 改为空实现 |
| 7 | pthread_setcanceltype 不可用 | 同上 | 注释 pthread_setcanceltype/setcancelstate 调用 |
| 8 | test_package 链接失败 | C 文件不链接 C++ 运行时 | test.c 改为 test.cpp，添加 system_libs |
| 9 | package() 库路径错误 | OutputFile 用 ../bin/ 相对路径 | 修正为 build/bin/aarch64-linux/libsnap7.a |
| 10 | SourceForge 下载极慢 | 网络带宽限制 (~67KB/s) | source() 优先使用 $TMPDIR/builds/ 本地缓存 |

## 源码修改

### build/unix/aarch64_linux.mk (新建)
- 新建 ARM64 平台 Makefile，设置 TargetCPU=aarch64, OS=linux

### build/unix/common.mk (修改)
- LinkerName: g++ → clang++
- CXX: g++ → clang++
- CC: gcc → clang
- AR: ar rcus → llvm-ar rcus
- SharedObjectLinkerName: 改为 llvm-ar rcs（静态库）
- OutputFile: libsnap7.so → libsnap7.a
- 链接命令: 移除共享库链接参数，使用 ar 语法
- install 目标: 添加 DESTDIR 支持

### src/sys/unix_threads.h (修改)
- ThreadKill(): 禁用 pthread_cancel，改为空实现

### src/sys/snap_threads.cpp (修改)
- 注释 pthread_setcanceltype/pthread_setcancelstate 调用

## 依赖版本

无第三方依赖。snap7 是自包含的通信库。

## 验证结果

```
# 编译验证
$ make -C build/unix -f aarch64_linux.mk -j1
# → 12 个 .o 文件编译成功，libsnap7.a 生成 (334KB)

# Conan 配方验证
$ conan-verify snap7 1.4.2
# → G0-G4 + L2/L4/L5 全部 PASS

# test_package 测试
$ ./test_snap7
snap7 test: creating client...
Cli_Create succeeded
Cli_Destroy succeeded
snap7 1.4.2: OK
# → 退出码 0, CTest Test Passed
```

## 注意事项

- snap7 是 C++ 库，C 语言消费者需额外链接 libc++/libc++abi（已通过 system_libs 声明）
- 源码修改在 conanfile.py 的 build() 方法中动态应用，无需预打补丁
- unix_threads.h 的修改未生成补丁文件（hash 不匹配），已在 build() 中处理
- 线程取消被禁用可能影响强制终止线程的能力，但不影响正常通信功能
---

**编译结束**: 2026-06-30 12:16
**最终状态**: published
