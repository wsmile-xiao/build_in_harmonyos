# kea-perfdhcp

ISC Kea 的 **perfdhcp**（DHCP 性能压测客户端），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`perfdhcp` 是 Kea 自带的 DHCP 性能/压力测试工具：按指定速率向被测服务器发起
DHCPv4（DISCOVER/OFFER/REQUEST/ACK）或 DHCPv6（SOLICIT/ADVERTISE/REQUEST/REPLY）
交换，支持 basic / avalanche 两种场景与多线程模式，运行中周期性输出速率、时延
（min/avg/max/标准差）与丢包统计，可用 `-n`（交换次数）、`-p`（测试时长）、
`-D`（最大丢包数/百分比）控制退出条件。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/bin/perfdhcp/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：上游 `SBINDIR`（本包按 Conan 约定安装到 `bin/perfdhcp`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带客户端运行期加载的 10 个 Kea 共享库（`readelf -d` NEEDED 闭包，
含 soname 符号链接），因此安装后无需额外的 Kea 运行库即可直接执行。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
4. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。

## 上游测试

`src/bin/perfdhcp/tests/meson.build` 注册 1 个 gtest 套件 `perfdhcp-tests`
（13 个子套件 / 140 个用例），在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `perfdhcp-tests` | 140 | AvalancheScenTest(6)、BasicScenTest(7)、LeaseTypeTest(6)、CommandOptionsTest(50)、PacketStorageTest(5)、PerfPkt4Test(8)、PerfPkt6Test(6)、RateControl(5)、Receiver(2)、StatsMgrTest(10)、TestControlTest(33)、LocalizedOptionTest(1)、PerfSocketTest(1) |

本版本实测：140/140 通过，0 失败，0 跳过。

## test_package（消费者视角 + 鸿蒙特有用例）

`conan create` 的 test 阶段真实编译并执行 3 个测试（CMake + `find_package(kea-perfdhcp)`）：

| 测试 | 断言 | 内容 |
|------|------|------|
| `test_perfdhcp.py` | 11 | 版本输出（`-v`/`-V`）、`-h` usage、非法 `--scenario` 拒绝路径、一次真实 IPv6 交换尝试 |
| `test_ohos_platform`（**鸿蒙特有**） | 8 | 包内 `bin/perfdhcp` 的 OHOS 平台 ABI 特征：ELFCLASS64 / `EM_AARCH64` / `ET_DYN`(PIE)、`DT_NEEDED` 链接 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so` |
| `test_ohos_runtime`（**鸿蒙特有**） | 6 | OHOS 加载器下的运行时闭包：`DT_NEEDED` 的 Kea 库全部随包分发、10 个 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功、真实执行 `perfdhcp -v` 输出 `3.0.3` |

鸿蒙特有测试用例 **2 个**，实测 **2/2 通过**。

## 使用

```bash
conan install --requires=kea-perfdhcp/3.0.3 -pr:h=<ohos-aarch64 profile>

# 版本
perfdhcp -v
perfdhcp -V

# 对 DHCPv6 服务器压测（100 次 SARR 交换，最大丢包 3 个）
perfdhcp -6 -r 100 -n 100 -D 3 -l <iface> <server-address>
```
