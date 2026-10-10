# Intel(R) PCM

> Intel Platform Characterization Monitor：跨平台的性能与能耗指标采集 API 与命令行工具集

## 简介

Intel PCM 是一组用于采集 x86 平台性能计数器（core PMU、uncore、内存控制器、
PCIe、QPI/UPI）和功耗数据的命令行工具，同时提供 `libpcm` 作为二次开发用的
可移植 API。上游以 `pcm`（通用）、`pcm-power`、`pcm-memory`、`pcm-core`、
`pcm-raw`、`pcm-accel`、`pcm-tsx`、`pcm-tpmi` 等 20 个工具的形式发布，并附带
一个 daemon/client 对，用于把采样放到常驻进程里。

本归档是 `pcm` **202502** 在 **HarmonyOS PC（OHOS / aarch64）** 上的适配版本。
上游工程本身只面向 Intel x86 CPU，因此在 aarch64 上需要一组可移植性补丁：
CPUID、RDTSC/RDTSCP、线程亲和性三处 x86/glibc 专有接口，以及
`pthread_cancel()` 的可用性探测。补丁只改「怎么问平台要数据」，不改 PCM 自己的
算法与统计逻辑。

## OHOS 适配要点

- **不伪造 CPU 身份。** aarch64 没有 CPUID 指令，`pcm_cpuid()` 在非 x86 上返回
  保留的零叶子，于是工具启动时如实打印
  `Error: unsupported processor. Only Intel(R) processors are supported ...`。
  这条断言是本归档 test_package 的核心检查项。
- **周期计数器换成架构等价物。** aarch64 用 `CNTVCT_EL0` 虚拟计数器代替 RDTSC，
  `RDTSCP()` 的辅助值取 `TPIDR_EL0`。
- **线程亲和性用 POSIX 接口。** `sched_getaffinity()` / `sched_setaffinity()`
  取代 glibc 专有的 `pthread_*_affinity_np()`。
- **`CMAKE_SYSTEM_NAME` 必须显式设成 `Linux`。** Conan 的 `CMakeToolchain` 会把
  `os=OHOS` 映射成 CMake 不认识的 `HarmonyOS`，上游的 `if(UNIX)` 分支会整段消失；
  HarmonyOS PC 跑的是 Linux 内核与 musl libc，配置成 `Linux` 才是上游分支描述的
  真实环境。
- **功能边界要说清楚。** 采样本身依赖 Intel x86 PMU 与 MSR/PCI 配置空间访问，
  HarmonyOS PC 上没有这些硬件接口，工具会如实报告
  `Access to Intel(r) Performance Counter Monitor has denied (no MSR or PCI CFG space access)`；
  也就是说本归档交付的是**完整可用、可编译、可运行**的 20 个工具，
  而性能计数数值需要在 Intel 硬件上才有意义。

## 排除与替代

- `pcm-msr` / `pcm-pcicfg` 直接读写 MSR 与 PCI 配置空间，在 HarmonyOS PC 上没有
  对应接口，运行时会报告访问被拒；其余工具不受影响。
- 上游 `tests/test.sh` 需要 `modprobe msr`、`/proc/sys/kernel/nmi_watchdog` 与
  Intel x86 PMU，不在本归档的验证范围内（详见 `202502/test_package/MANIFEST.yml`）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| simdjson | 3.9.5 | `pcm-raw` 解析 Intel perfmon 事件 JSON；上游 tarball 里 `src/simdjson` 是空的子模块目录，所以依赖必须来自制品仓 |
| openssl | 3.0.21 | `pcm-sensor-server` 默认启用 OpenSSL 支持；保持上游默认而不是把守护进程降级成明文 socket 协议 |

## 功能验证

```bash
# 版本身份（构造 PCM 对象之前处理，不需要 PMU 访问）
pcm --version
# -> version: (2025-02-25 10:03:48 +0100 ID=5cb70ffd)

# 非 Intel CPU 上的诚实报告
pcm
# -> Error: unsupported processor. Only Intel(R) processors are supported (...)
# -> Access to Intel(r) Performance Counter Monitor has denied (no MSR or PCI CFG space access).

# 第二个独立编译的工具也走到 uarch 分派
pcm-power
# -> Unsupported processor model (0xffffffff).

# perfmon 事件表随包安装（pcm-raw 运行时读取）
ls "$(dirname "$(command -v pcm)")"/../share/pcm/opCode-*.txt
```

完整的 16 条断言见 `202502/test_package/test.sh`。

## 参考

- [官方文档](https://github.com/intel/pcm/blob/master/doc/PCM_How_To.md)
- [源码仓库](https://github.com/intel/pcm)