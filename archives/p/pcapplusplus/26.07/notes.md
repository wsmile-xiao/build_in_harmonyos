# pcapplusplus 26.07 适配笔记

## 构建配置

- 分支：`feat/pcapplusplus-26.07`（与平台任务登记名逐字符一致）
- 任务类型：依赖项（语言 C++）；难度 ⭐2
- 构建系统：CMake（上游 `cmake_minimum_required(VERSION 3.12)`，库使用 C++14）
- 包类型：library（默认静态；`shared` 选项可切动态）
- 依赖：`libpcap/1.10.6`（ohpcd 制品仓已有：armv8 / OHOS / clang 15 / libc++ / 静态）
- 源码：`https://github.com/seladb/PcapPlusPlus/archive/refs/tags/v26.07.tar.gz`
  sha256 `58efbebde9df37134ca6abffdc585562155b7fc0937ced1fd6569a8c93a22ba6`
  （与 `codeload.github.com/seladb/PcapPlusPlus/tar.gz/refs/tags/v26.07` 实测同一 tarball，
  145 字节级一致，实测下载 14,831,861 字节）
- 补丁：**无**。本适配完全通过 Conan 配方（缓存变量注入）达成，未改动上游任何文件。

## OHOS 适配要点

1. **E092：CMake 无 HarmonyOS 平台模块 → 强制 `CMAKE_SYSTEM_NAME=Linux`。**
   本机 clang 目标三元组为 `aarch64-unknown-linux-ohos`，CMake 4.1.2 会把目标系统识别为
   `HarmonyOS` 并打印 `System is unknown to cmake, create: Platform/HarmonyOS`，随后落到
   通用分支，`UNIX`/`LINUX` 变量均为假。上游 `CMakeLists.txt` 用
   `if(UNIX AND NOT APPLE AND NOT CYGWIN AND NOT ANDROID) set(LINUX True)` 判定 Linux 分支，
   而 `Pcap++/CMakeLists.txt` 用 `$<$<BOOL:${LINUX}>:src/LinuxNicInformationSocket.cpp>`
   决定是否编译该翻译单元。实测不设置时，`build.ninja` 中 **0 处** 引用
   `LinuxNicInformationSocket`（该源被静默丢弃，安装产物缺少 `NicInformationSocket`）；
   设置后变为 3 处。配方在 `generate()` 里写 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"`
   （与已合入的 libtins/4.5 同一手法）。

2. **libpcap 经上游自带 `cmake/modules/FindPCAP.cmake` 发现，不是 CMake config 包。**
   该模块用 `find_path(PCAP_INCLUDE_DIR NAMES pcap/pcap.h pcap.h ...)` 与
   `find_library(PCAP_LIBRARY NAMES pcap wpcap)` 查找，并提供 `PCAP::PCAP` 导入目标。
   配方在 `generate()` 里从 `self.dependencies["libpcap"]` 取包目录，把
   `PCAP_INCLUDE_DIR=<pkg>/include`、`PCAP_LIBRARY=<pkg>/lib/libpcap.a` 直接写入缓存变量，
   不依赖 CMAKE_PREFIX_PATH 的搜索顺序。实测 `Found PCAP: .../lib/libpcap.a
   (found version "1.10.6 (64-bit time_t, with TPACKET_V3)")`，
   `HAVE_PCAP_IMMEDIATE_MODE` / `HAVE_PCAP_TIMESTAMP_TYPES` / `HAVE_PCAP_TIMESTAMP_PRECISION`
   三项探测全部命中（`pcap_set_immediate_mode`、`pcap_list_tstamp_types`、
   `pcap_set_tstamp_precision` 均可用）。

3. **静态 libpcap 与 `FindPCAP.cmake` 的链接探测**：`check_cxx_source_compiles("int main(){return 0;}")`
   在 `CMAKE_REQUIRED_LIBRARIES=libpcap.a` 下通过（归档中无被引用符号时链接器不拉取成员），
   故 `PCAP_LINKS_SOLO` 为真，不会落入 "Couldn't determine how to link against libpcap" 的
   FATAL_ERROR 分支。

4. **无需补丁**：上游 `FindPCAP.cmake` 的版本探测有 `if(NOT CMAKE_CROSSCOMPILING)` 保护；
   本机构建与目标架构一致（aarch64 本机编译本机），`try_run` 正常返回
   `"1.10.6 (64-bit time_t, with TPACKET_V3)"`。全流程 `conan create` 退出码 0。

## 上游测试接入

上游使用**自研 PTF 框架**（`Tests/PcppTestFramework/PcppTestFrameworkRun.h`），无 gtest 依赖。
测试注册在 `main.cpp` 的 `PTF_RUN_TEST(<Name>, "<tags>")`，结果汇总行固定格式：

```
Test cases: <total>, Passed: <p>, Failed: <f>, Skipped: <s>
```

返回码 = 全通过 ? 0 : 1。两个可执行文件：

| 二进制 | 注册用例 | 运行方式 | 说明 |
|--------|---------|---------|------|
| `Tests/Packet++Test/Packet++Test` | 259 | 无参 | 完全离线：解析 `PacketExamples/*.dat` 固件（469 个文件） |
| `Tests/Pcap++Test/Pcap++Test` | 113 | `-n -x live_device` | `-n` 只跑 `no_network` 标签用例；`-x live_device` 再排除 2 个网卡枚举用例 |

- 上游 `ctest` 条目（`Tests/*/CMakeLists.txt` 的 `add_test`）共 2 个：
  `Packet++Test`（无参）、`Pcap++Test -n`。
- **`live_device` 被显式排除的原因（诚实说明）**：`TestPcapLiveDeviceList` 与
  `TestPcapLiveDeviceNoNetworking` 需要 libpcap 成功枚举本机网卡。构建沙箱下
  `ls /sys/class/net` 即 `Permission denied`，`SIOCETHTOOL(ETHTOOL_GLINK)` ioctl 返回
  `EPERM`，于是 `pcap_findalldevs()` 整体失败并抛出
  `Error searching for devices: dummy0: SIOCETHTOOL(ETHTOOL_GLINK) ioctl failed: Permission denied`，
  `PcapLiveDeviceList` 为空，两个用例必然 `PTF_ASSERT_FALSE(devList.empty())` 失败。
  这不是本库的移植缺陷（`/proc/net/dev` 里只有 `lo`/`dummy0`/`tunl0` 等虚拟设备，
  沙箱不授予网络设备枚举权限），故按上游自带标签机制排除，其余 69 个 `no_network` 用例全跑。
  实测两轮：`Pcap++Test -n` → `69 passed / 2 failed / 42 skipped`；加 `-x live_device` 后
  `69 passed / 0 failed / 44 skipped`。

## 验证

- 真机（本机即 OHOS PC aarch64，`conan create --build=missing`，默认 OHOS profile）：
  - 上游测试：
    - `Packet++Test`：**259/259 通过，0 失败，0 跳过**
    - `Pcap++Test -n -x live_device`：**69/69 执行用例通过，0 失败，44 跳过**
      （跳过项为网络/GUI/DPDK/PF_RING/XDP 等本构建未启用的特性标签用例，
      以及 2 个沙箱不可用的 live_device 用例）
    - 上游合计：注册 **372** 个用例，实际执行 **328** 个，**328/328 通过**，跳过 44 个
  - 消费者测试（test_package，`test_pcapplusplus`）：**36/36 断言通过**
    （`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
    "discovered": 36, "passedCount": 36}`，与 `test_package/MANIFEST.yml` 的
    `assertion_count: 36` 同源）
  - 编译告警：全量构建仅 6 条告警（上游 `-Wall` 下的既有告警），0 error。
- 适配后测试用例统计（PR 正文四行口径）：
  - 鸿蒙特有测试：5（本配方消费者测试内的平台属性断言：`__OHOS__` 目标宏、LP64
    `sizeof(void*)==8`、`sizeof(long)==8`、小端、64 位 `timespec`）
  - PC特有测试：0（PcapPlusPlus 为通用跨平台网络库，无 PC 桌面形态特有行为需单列）
  - 消费者用例：1（`test_package/test_pcapplusplus.cpp` 消费者程序）
  - 消费者测试：36（上述程序的 36 条断言，不重复计入合计）

## 已知限制

- 构建沙箱无网络设备枚举权限，`live_device` 类上游用例（2 个）无法执行，已在配方中显式
  用上游标签机制排除并在本文件与 `test_package/MANIFEST.yml` 中说明。
- 上游 `Examples` 与 `Fuzzers` 未构建（`PCAPPP_BUILD_EXAMPLES=OFF`，默认即不构建），
  二者不含 ctest 用例。

## 路径判定

结论：**路径 A（基础适配）**，不申报路径 B。理由：本次适配手法均为仓内既有知识的应用——
- 强制 `CMAKE_SYSTEM_NAME=Linux` 是知识库 E092 的既有条目（libtins/4.5 已用）；
- 把 Conan 依赖包路径注入上游 `find_path`/`find_library` 型自研 Find 模块，是常规依赖桥接；
- OHOS 下用 `CONFIG_SHELL`(hnp bash) 启动、`binary-sign-tool` 自签，均为既有环境惯例；
- 未形成可跨仓库复用的新增独立主题。

---

**编译结束**: 2026-09-24
**最终状态**: built
