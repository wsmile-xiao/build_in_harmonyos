# cmake 4.3.4 适配笔记

## 编译环境
- 构建系统: cmake (Ninja generator)
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15.0.4 (OHOS SDK)
- 状态: built

## 编译步骤

1. `conan create` 驱动（见 conanfile.py）：下载官方源码（sha256 校验）→ 应用 4 个补丁 →
   `cmake -G Ninja` 配置（conan_toolchain 注入 ncurses/openssl 静态库路径）→ `cmake --build`。
2. 关键配置变量：`CMAKE_SYSTEM_NAME=Linux`（见下文问题 #1）、`BUILD_CursesDialog=ON`（ccmake）、
   `CMAKE_USE_SYSTEM_LIBRARIES=OFF`（内置依赖自包含）、`OPENSSL_USE_STATIC_LIBS=TRUE`。
3. test_package 冒烟：test_cmake 驱动被测包 cmake 完成 `--version` → configure → build →
   运行产物 hello（见 test_package/test.c）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | kwsys 编译 ProcessWin32.c 报 `windows.h not found` | CMake 4.3.4 只有 Platform/OHOS.cmake（include Linux），无 HarmonyOS.cmake；conan toolchain 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，UNIX 变量不置位 | 配方强制 `CMAKE_SYSTEM_NAME=Linux`（知识 E092 同源） |
| 2 | cmAffinity/cmlibuv 链接错误 `pthread_getaffinity_np undefined` | 该 API 是 glibc 扩展，OHOS musl 不提供；`__linux__` 在 OHOS clang 上仍为 1 | 补丁 0001/0003/0004：守卫改为 `defined(__linux__) && defined(__GLIBC__)`，musl 上禁用 CPU affinity（ENOTSUP） |
| 3 | cmcurl 5 个文件报 `sockaddr_storage redefinition` | OHOS 内核头 linux/tcp.h → linux/socket.h 与 musl sys/socket.h 重复定义 | 补丁 0002：`check_c_source_compiles` 编译期探针，同时包含两个头编译失败则 HAVE_LINUX_TCP_H=0（glibc 上仍启用） |
| 4 | toybox make + jobserver 嵌套死锁（conan→make→sh 卡 rt_sigsuspend） | toybox sh 在嵌套 jobserver 环境下 spawn 子进程挂起；bootstrap 阶段还有 mkfifo jobserver `Operation not permitted` | 配方显式 `generator="Ninja"`（cmake_layout + CMakeToolchain 双处）；test_package 的 test() 直接运行二进制而非 cmake.test() |
| 5 | openssl/ncurses 依赖路径解析 | conan2 包缓存为 `<pkg>/p/{include,lib}` 布局，cpp_info 返回 conan-layout 路径 | conanfile.py generate() 中 "/p" 目录推导（含兜底探测） |

## 源码修改（patches/）

- `0001-Source-cmAffinity.cxx.patch` — CPU affinity 守卫加 `__GLIBC__`（musl 禁用）
- `0002-Utilities-cmcurl-CMakeLists.txt.patch` — linux/tcp.h 编译期冲突探针
- `0003-Utilities-cmlibuv-src-unix-core.c.patch` — uv_cpumask_size musl 返回 ENOTSUP
- `0004-Utilities-cmlibuv-src-unix-process.c.patch` — 子进程 cpu-affinity 设置跳过 musl
- `0005-Modules-Platform-HarmonyOS.cmake.patch` — 新增宿主平台模块：被测 cmake 原生运行于
  HarmonyOS（uname -s=HarmonyOS）时不再报 "System is unknown"（include Platform/Linux，
  与 Platform/OHOS.cmake 同构）
- `0006-Source-kwsys-SystemInformation.cxx.patch` — /proc/meminfo 格式按内容探测：
  HongMeng 内核版本号（1.13.0）低于 2.6 阈值但提供新格式，仅按版本判断会走旧解析
  路径失败并污染 stderr（"Problem parsing /proc/meminfo"）

所有补丁新增行不含平台宏（PF5 合规），用 libc/内核行为守卫，glibc Linux 行为不变。

## 依赖版本

- ncurses/6.6（静态 libncursesw.a，ccmake 链接；R26 不污染系统 /lib）
- openssl/3.5.6（静态 libssl.a/libcrypto.a，内置 cmcurl https 支持）

## 验证结果

```bash
$ conan create（BUILD_TESTING=ON）
  # build() 内 ctest 真实执行上游单元测试子集 kwsys.* + CMakeLib.*：66 项 62 通过
  # 4 项沙箱限制排除：文件系统忽略 chmod 权限位、unix-socket bind 被拒
$ conan-verify cmake 4.3.4   # G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
$ W3 本地 CI 模拟             # L0 pass / L1 pass / L2 pass (4 工具 --version) / L5 pass
$ ccmake --version            # ccmake version 4.3.4
$ readelf -d bin/ccmake       # NEEDED: libc++_shared.so, libc.so（ncurses 已静态链入）
```

## 上游测试执行（BUILD_TESTING=ON）

上游 Tests/ 目录 292 个子目录，BUILD_TESTING=ON 构建后 `ctest -N` 实测注册 659 项。
本地真实执行分层情况：

| 子集 | 注册数 | 执行 | 通过 | 未执行/排除原因 |
|------|--------|------|------|------------------|
| kwsys.*（单元） | 20 | 19 | 19 | 1 排除：testSystemTools（沙箱 chmod 权限位不生效，SetPermissions 断言无法成立） |
| CMakeLib.*（单元） | 46 | 43 | 43 | 3 排除：testDebuggerAdapterPipe / testDebuggerNamedPipe-Project / -Script（沙箱 unix-socket bind: Operation not permitted） |
| RunCMake.*（功能） | 353 | 抽样 | 修复 0005/0006 前 48 连败（stderr 污染），修复后抽样批次约 85%+ 通过；剩余失败均为沙箱限制（chmod/符号链接/网络下载/try_compile 嵌套构建超时） | 不可全量运行：需网络（file-DOWNLOAD）、宿主 git/python、嵌套 try_compile 构建超预算 |
| 其余（CTest*/CPack*/Find* 等） | 240 | — | — | 需网络/宿主工具/守护进程（dash、coverage 工具链等） |

打 0005/0006 补丁前的失败根因（已修复）：被测 cmake 原生运行时探测宿主系统名
HarmonyOS 无平台模块 → "System is unknown" 警告污染每个 RunCMake 用例的 stderr；
HongMeng 内核版本号 1.13.0 < 2.6 阈值 → kwsys 走旧 /proc/meminfo 解析失败。
修复后原生 configure 已零 stderr 输出。

## 注意事项

- CI 侧 conan toolchain 若将 CMAKE_SYSTEM_NAME 设为 HarmonyOS 将复现问题 #1，配方已强制 Linux 规避。
- 不要改回 make 生成器：toybox jobserver 死锁会导致 CI/本地构建挂起（无错误输出，只能超时）。
- 嵌套 make（如 ctest 经 make）同样会死锁；如需扩展测试，直接运行二进制。
