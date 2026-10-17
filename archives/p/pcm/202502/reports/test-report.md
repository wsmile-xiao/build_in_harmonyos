# pcm 202502 测试报告（HarmonyOS PC / OHOS aarch64）

- 包：`pcm/202502`
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, compiler=clang 15, libcxx=libc++, cppstd=17）
- 命令：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
- 结果：**通过**（test_package 16/16 断言；上游可移植测试 1/1）

## 上游测试

上游 `tests/` 下共 4 个文件：`CMakeLists.txt`、`daemon_alignment_test.cpp`、
`urltest.cpp`、`test.sh`，外加 4 个只在 `PCM_FUZZ=ON` 时才编的 `*-fuzz.cpp`。
CMake **没有**注册任何 ctest 测试，也**没有** `make check` 目标——上游测试程序就是
`bin/tests/` 下的普通可执行文件。

| 上游测试 | 是否执行 | 位置 | 说明 |
|----------|----------|------|------|
| `tests/daemon_alignment_test` | ✅ 已执行 | `conanfile.py build()` | 架构无关：分配 `PCMDaemon::SharedPCMState` 并校验每个成员保持 64 字节对齐，首个错位即 `exit(EXIT_FAILURE)`。退出 0 |
| `tests/urltest` | ❌ 未执行 | — | 需要向 sensor server 开 loopback HTTP 连接 |
| `tests/test.sh` | ❌ 未执行 | — | 首行即 `modprobe msr`，并写 `/proc/sys/kernel/nmi_watchdog`，需要 Intel x86 PMU 与 root |

> 未执行的两项按实记录在 `test_package/MANIFEST.yml`，**不计入通过数**。

## test_package 消费者用例

`test_package/test.sh` —— 16 条断言，全部实跑打包产物并检查真实输出或真实 ELF 属性。

| # | 断言 | 类型 |
|---|------|------|
| 1 | `pcm --version` 退出 0 | 运行时 |
| 2 | `pcm --version` 报上游 202502 build id `ID=5cb70ffd` | 运行时 |
| 3 | `pcm --help` 打印 Usage 块 | 运行时 |
| 4 | `pcm-memory --help` 打印 Usage 块 | 运行时 |
| 5 | `pcm-power --help` 打印 Usage 块 | 运行时 |
| 6 | `pcm-raw` **不是** 无 simdjson 的降级构建（降级提示不得出现） | 运行时 |
| 7 | `pcm`（无参数）如实报 `Error: unsupported processor. Only Intel(R) processors are supported`，未伪造 CPUID 数据 | 运行时 · HarmonyOS 专项 |
| 8 | `pcm`（无参数）如实报 PMU 访问结果 `no MSR or PCI CFG space access` | 运行时 · HarmonyOS 专项 |
| 9 | `pcm-power`（无参数）走到 uarch 分派并报 `Unsupported processor model` | 运行时 · HarmonyOS 专项 |
| 10 | `readelf -h bin/pcm` 报 `Machine: AArch64` | 产物 · HarmonyOS 专项 |
| 11 | 全部打包 ELF 可执行文件都是 AArch64（无 x86_64 残留） | 产物 · HarmonyOS 专项 |
| 12 | 上游 20 个命令行工具全部打包（含 daemon/client 对） | 产物 |
| 13 | `pcm-client` 能运行并打出自己的 usage（`pollMs`） | 运行时 · HarmonyOS 专项 |
| 14 | `share/pcm/opCode-*.txt` 与 `PMURegisterDeclarations/` 已安装 | 产物 |
| 15 | 上游 shell 助手 `pcm-bw-histogram` 已安装且可执行 | 产物 |
| 16 | `share/licenses/pcm/LICENSE` 与 `share/doc/PCM/README.md` 已安装 | 产物 |

实测输出：

```
assertions_total=16 pass=16 fail=0
```

## 本地 x86 执行环境的条件 shim（已披露）

交付的 20 个产物都只 `NEEDED libc.so`，链接的是真实 HarmonyOS libc——它导出
`__memset_chk` 等 `__*_chk` fortify helper 以及 `backtrace()` /
`backtrace_symbols()`（上游 `src/utils.cpp` 用到）。当 x86 构建机通过 musl guest
runtime 执行这些 aarch64 镜像时，该 runtime 可能是缺这些符号的旧 libc，loader 会在
`main()` 之前以 exit 127 终止。

这是**本地执行环境**的属性，不是包的缺陷：原生 OHOS CI worker 用真 libc 跑同一批
二进制，不需要任何 preload。因此 `test_package/test.sh`：

- 按**文件存在与否**条件注入 shim；
- 只作用于被启动的那一个 aarch64 进程（用函数包装，绝不 `export LD_PRELOAD` 到全脚本，
  否则每个 x86 辅助进程都会去预加载 aarch64 对象）；
- shim 是**转发桩**：`__memset_chk` / `__memcpy_chk` / `__send_chk` 真调
  `memset()` / `memcpy()` / `send()`；`backtrace()` 返回 0、`backtrace_symbols()`
  返回 NULL，等价于「该 libc 未启用栈回溯」，与上游 `utils.cpp` 里
  `if (backtrace_strings == NULL)` 分支一致。
- shim **不进配方、不进包**；真机上文件不存在，走完全相同的直调分支。

## 未覆盖的能力边界

采样数值依赖 Intel x86 PMU 与 MSR / PCI 配置空间访问，HarmonyOS PC 没有这些硬件
接口。工具如实报告 `Access to Intel(r) Performance Counter Monitor has denied
(no MSR or PCI CFG space access)` 并以非零码退出——这是正确行为，不是缺陷。
本归档交付的是完整可编译、可运行的 20 个工具；计数数值本身需在 Intel 硬件上才有意义。