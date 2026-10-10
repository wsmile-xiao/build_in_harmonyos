# pcm 202502 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-04
- 编译器: clang/clang++（OHOS NDK，`/data/service/hnp/bin/clang`，clang 15）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, libcxx=libc++, cppstd=17）
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. `source()`：`get(self, **self.conan_data["sources"], strip_root=True)` 拉官方 tag 归档
   `https://github.com/intel/pcm/archive/refs/tags/202502.tar.gz`，
   sha256 `431bd5f7122ec909634b02a05ce1eb898834f5c2b19d2804e27f5496cc6eba49`
3. `build()`：先 `apply_conandata_patches(self)` 打 5 个补丁，再 `cmake.configure()` / `cmake.build()`
4. `build()` 末尾实跑上游自带测试程序 `bin/tests/daemon_alignment_test`（架构无关），
   产物缺失时只告警不假装通过
5. `package()`：`CMake(self).install()`

关键 CMake 缓存变量（全部由配方注入，未改上游工程文件）：

| 变量 | 值 | 原因 |
|------|----|------|
| `CMAKE_SYSTEM_NAME` | `Linux` | Conan 的 CMakeToolchain 把 `os=OHOS` 映射成 CMake 不认识的 `HarmonyOS`，上游 `if(UNIX)` 分支会整段消失 |
| `CMAKE_POLICY_VERSION_MINIMUM` | `3.5` | 上游 `cmake_minimum_required` 低于 CMake 4 兼容下限 |
| `CMAKE_INSTALL_SBINDIR` | `bin` | 上游把 CLI 装进 sbin，Conan 消费者按标准 bindir 查找 |
| `PCM_NO_ASAN` / `PCM_NO_STATIC_LIBASAN` | `ON` | 上游默认开 ASan，OHOS 镜像不带 sanitizer runtime |
| `PCM_BUILD_EXECUTABLES` | `ON` | 显式保留上游全部 20 个工具 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 编译直接失败在 `src/types.h` 的 `cpuid` 内联汇编 | CPUID 是 x86 专有指令 | 补丁 0001：非 x86 返回保留的零叶子，绝不伪造 Intel CPU 身份 |
| 2 | 编译失败在 `src/cpucounters.h` 的 `rdtsc` / `rdtscp` 内联汇编 | RDTSC/RDTSCP 同样是 x86 专有 | 补丁 0002：aarch64 改读 `CNTVCT_EL0`，辅助值取 `TPIDR_EL0`；其它架构 `#error` |
| 3 | 编译失败在 `src/utils.h` 的 `pthread_getaffinity_np` / `pthread_setaffinity_np` | glibc 专有扩展，musl 系 libc 没有 | 补丁 0003：改用 POSIX `sched_getaffinity(0,…)` / `sched_setaffinity(0,…)` |
| 4 | 链接/编译假设 `pthread_cancel()` 存在 | 部分 musl 派生 libc 不实现 pthread_cancel | 补丁 0004：configure 期 `check_symbol_exists()` 探测，缺失时析构函数如实打印限制 |
| 5 | `examples/c_example.c` 里 `pcm_getcpu()` 用 `rdtscp` 取 CPU 号 | RDTSCP 是 x86 专有 | 补丁 0005：非 x86 改用 POSIX `sched_getcpu()` |
| 6 | Conan 生成的工具链让上游 `if(UNIX)` 整段消失 | `os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 无此取值 | 配方显式 `CMAKE_SYSTEM_NAME=Linux` |
| 7 | `pcm-raw` 悄悄退化成无 simdjson 的构建 | 上游 tarball 里 `src/simdjson` 是空子模块目录，CMake 找不到就走降级路径且**构建照样成功** | 声明 `simdjson/3.9.5` 依赖；断言检查降级提示「compiled without simdjson library」**不出现** |
| 8 | x86 构建机上跑打包产物全部 exit 127 | 交付物链接的是真 HarmonyOS libc（导出 `__*_chk` 与 `backtrace()`），而本地 qemu 用的 musl guest runtime 是旧 libc，缺这些符号，loader 在 main() 之前就退出 | test.sh 里**按文件存在与否**条件注入本地 shim，且只作用于被启动的那个 aarch64 进程（不 export 到全局）；真机 OHOS CI worker 上这些文件不存在，走完全相同的直调分支。shim 是转发桩（`__memset_chk` 等真调 `memset()`，`backtrace()` 返回 0），不进配方、不进包 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | `src/types.h` | `pcm_cpuid()` 两个重载：CPUID 指令只留在 `__x86_64__`/`__i386__`，其它架构清零 `info.array` 并返回 |
| 0002 | `src/cpucounters.h` | `RDTSC()` → `mrs %0, cntvct_el0`；`RDTSCP()` → `cntvct_el0` + `tpidr_el0`；未知架构 `#error` |
| 0003 | `src/utils.h` | `TemporalThreadAffinity` 构造/析构改用 `sched_getaffinity(0,…)` / `sched_setaffinity(0,…)`，错误信息同步更新 |
| 0004 | `src/CMakeLists.txt`, `src/cpuasynchcounter.h` | `check_symbol_exists(pthread_cancel …)` → `PCM_HAVE_PTHREAD_CANCEL`；析构函数在缺失时打印真实限制 |
| 0005 | `examples/c_example.c` | `pcm_getcpu()`：x86 保持 `rdtscp`，其它架构用 `sched_getcpu()` |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| simdjson | 3.9.5 | Conan 制品仓 `ohpcd`（上游 tarball 的子模块目录是空的） |
| openssl | 3.0.21 | Conan 制品仓 `ohpcd`（`pcm-sensor-server` 默认启用） |

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
pcm/202502 (test package): Test package build folder: .../test_package
pcm/202502 (test package): Running test()
PASS [1] pcm --version exits 0
PASS [2] pcm --version reports the upstream 202502 build id
PASS [3] pcm --help prints its usage block
PASS [4] pcm-memory --help prints its usage block
PASS [5] pcm-power --help prints its usage block
PASS [6] pcm-raw is not the no-simdjson fallback build
PASS [7] pcm reports the non-Intel CPU honestly instead of fabricating CPUID data
PASS [8] pcm reports the real outcome of its PMU access attempt
PASS [9] pcm-power reaches PMU init and reports the real processor model
PASS [10] packaged pcm is an AArch64 ELF image
PASS [11] all packaged ELF tools are AArch64
PASS [12] all 20 upstream command line tools are packaged
PASS [13] pcm-client runs and prints its usage
PASS [14] perfmon opcode tables and PMU register declarations are installed
PASS [15] upstream pcm-bw-histogram helper is installed and executable
PASS [16] LICENSE and README.md are installed under share/

assertions_total=16 pass=16 fail=0
```

上游测试：`bin/tests/daemon_alignment_test`（架构无关）在 `build()` 里实跑，退出 0。
另两个上游入口 `tests/urltest`（需要 loopback HTTP）与 `tests/test.sh`
（需要 `modprobe msr` + `/proc/sys/kernel/nmi_watchdog` + Intel x86 PMU）
在 HarmonyOS PC 上不成立，按实记录在 `test_package/MANIFEST.yml`，不计入通过数。

## 交付边界（必须说清楚）

- 采样数值依赖 Intel x86 PMU 与 MSR / PCI 配置空间访问，HarmonyOS PC 没有这些
  硬件接口；工具会如实报告
  `Access to Intel(r) Performance Counter Monitor has denied (no MSR or PCI CFG space access)`。
- 本归档交付的是**完整可编译、可运行**的 20 个工具；性能计数数值本身需要在
  Intel 硬件上才有意义。