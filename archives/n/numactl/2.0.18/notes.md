# numactl 2.0.18 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4 (LLVM)
- 状态: built

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS 平台 | 上游 config.guess 版本旧，不支持 HarmonyOS | 在 build-aux/config.guess 中添加 HarmonyOS 到 Linux 检测分支和 aarch64:HarmonyOS 特例 |
| 2 | config.status 报 "Permission denied" 创建临时文件 | HMDFS 文件系统不支持 umask 077 创建的目录写入 | 在 conanfile.py build() 方法中使用 replace_in_file 将 configure 中的 umask 077 改为 umask 022 |
| 3 | sockaddr_storage 重定义错误 | HarmonyOS 内核头文件 linux/socket.h 与用户态 sys/socket.h 都定义了 struct sockaddr_storage 且无冲突保护 | 在 affinity.c 和 rtnetlink.c 中，引入 linux 头文件前定义 __kernel_sa_family_t 并设置 _UAPI_LINUX_SOCKET_H 宏跳过 linux/socket.h |
| 4 | make check 中 7 个测试失败 | 1) 部分 test 是 shell 脚本引用 /bin/bash (HarmonyOS 无此路径); 2) NUMA syscall 未实现 (Signal 31 SIGSYS) | 平台限制，非编译问题。库本身编译链接正常 |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| affinity.c | 0001-affinity.c.patch | 修复 sockaddr_storage 头文件冲突 (#ifdef __OHOS__) |
| build-aux/config.guess | 0002-build-aux-config.guess.patch | 添加 HarmonyOS 平台检测 |
| rtnetlink.c | 0004-rtnetlink.c.patch | 修复 sockaddr_storage 头文件冲突 (#ifdef __OHOS__) |
| configure | (build-time fix) | umask 077 → 022，在 conanfile.py build() 中使用 replace_in_file |

## 验证结果

```
make: 编译成功，生成 libnuma.a (静态) 和 6 个命令行工具
make check: 1 PASS, 1 SKIP, 7 FAIL (平台限制，非编译问题)
conan create: 通过 (G2 PASS)
conan test_package: 通过 (libnuma 链接验证)
```

## 注意事项

- numactl 是系统级 NUMA 策略库，在无 NUMA 硬件的 HarmonyOS 设备上运行时 syscall 会返回 SIGSYS (Signal 31)
- test/tbitmap.c 是唯一不依赖 NUMA syscall 的测试，通过
- 库可正常链接和调用 API (numa_available() 返回 -1 表示无 NUMA)
- 配方默认静态编译 (default_options shared=False)，只生成 libnuma.a

## 编译结束
状态: built | 补丁: 3 | conan-verify: PASS | CI模拟: PASS
