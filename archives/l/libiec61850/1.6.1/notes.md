# libiec61850 1.6.1 适配笔记

## 基本信息
- **软件名**: libiec61850
- **版本**: 1.6.1（tag `v1.6.1`，`git ls-remote` 实证）
- **构建系统**: CMake
- **上游仓库**: https://github.com/mz-automation/libiec61850
- **上游官网**: https://libiec61850.com/libiec61850
- **许可证**: LGPL-3.0（根目录 `COPYING`）
- **描述**: IEC 61850 协议栈（MMS / GOOSE / Sampled Values）的开源 C 实现，含客户端与服务端
- **包大小**: 源码 tarball 1,600,962 字节（约 1.6 MB）

## 依赖

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| （无 conan 依赖） | - | - | `requires()` 为空；系统库 pthread/m/rt 由 `package_info().system_libs` 声明 |
| mbedtls（可选） | - | `third_party/mbedtls`（上游自带） | 发布 tarball 中仅有 README，未随归档 → TLS / R-GOOSE / R-SMV 由上游自动关闭 |
| sqlite（可选） | - | `third_party/sqlite`（上游自带） | 同上 → sqlite-log 驱动与 `server_example_logging` 由上游自动关闭 |
| winpcap（可选） | - | `third_party/winpcap`（上游自带） | 仅 Windows 分支使用，Linux/OHOS 不需要 |

## W0 立项预检（生死关）

| 项 | 判据 | 读数 | 结论 |
|---|---|---|---|
| 版本可得性 | `git ls-remote --tags` | `refs/tags/v1.6.1` → `a13961110b8238d2d8ea577c1fb7592ba3017ad8` | ✅ |
| sha256 多路取证 | 本地下载 vs conan-center-index | 实测 `64113483eea8aec4f18cef9f8bb3c872585b2c67566824c4373db257bcc7bf8e`；CCI `recipes/libiec61850/all/conandata.yml` 同值 | ✅ 逐字一致 |
| 硬依赖 | `conan list "libiec61850/*" -r=ohpcd` + 配方 `requires()` | 0 个 conan 依赖（可选第三方组件缺失由上游门控处理，不算硬依赖） | ✅ |
| 平台可移植性 | ISA 专属头 grep（`altivec.h`/`mmx`/`3dnow`/`immintrin.h`/`arm_neon.h`…） | 0 命中 | ✅ |
| glibc printf 钩子 | `register_printf_*` / `<printf.h>` grep | 0 命中 | ✅ |

## 适配要点

### 1. CMake 平台识别（E092）
设备 `uname -s` 返回 `HarmonyOS`，CMake 4.1.2 无 `Platform/HarmonyOS.cmake`，
configure 打出 `System is unknown to cmake, create: Platform/HarmonyOS`，此时 `UNIX`
变量不成立 → `hal/CMakeLists.txt` 的 `ELSEIF(UNIX)` 分支不执行、`libhal_SRCS` 为空 →
`add_library` 报 **No SOURCES given to target: hal / hal-shared / iec61850 / iec61850-shared**。

处置：`generate()` 中在 `settings.os == "OHOS"` 时 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`
（HarmonyOS 基于 Linux 内核，知识条目 E092 的标准做法；仓库内已有 370 个配方同法）。
修复后 configure 全绿，`IF(UNIX)` 分支正常执行。

### 2. 以太网 HAL 头文件冲突（补丁 0001）
`hal/ethernet/linux/ethernet_linux.c` 原本 `#include <linux/if_arp.h>`。OpenHarmony SDK 的
该头会拉入 `<linux/netdevice.h>` → `<linux/if.h>` → `<linux/socket.h>`，后者**无条件**定义
`struct sockaddr_storage`，与先前包含的 `<sys/socket.h>` 冲突：

```
linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
sys/socket.h:377:8: note: previous definition is here
```

知识条目 E119/E091 属同族（其推荐方案用 `#ifdef __OHOS__` 守卫），但
`.gitcode/code-style.md` 的 **PF5 平台宏闸禁止 patches 新增行出现 `__OHOS__`**。
改用 POSIX 头一行到位（补丁 0001）：

```c
-#include <linux/if_arp.h>
+#include <net/if_arp.h>
+#include <net/if.h>
```

`<net/if_arp.h>` 提供 `ARPHRD_ETHER`，`<net/if.h>` 补齐 `struct ifreq` / `IFNAMSIZ` /
`IFF_PROMISC` / `IFF_ALLMULTI`；两头在 glibc/musl/BSD 上均存在，补丁本身可移植，
且不引入任何平台条件宏。补丁经 `patch -p1` 干净应用并与目标树 `cmp` 逐字节一致。

### 3. 上游测试面与可选组件
上游**没有 `tests/` 目录**，`ENABLE_TESTING()` 虽被调用，但唯一的 `add_test`
在 `pyiec61850/CMakeLists.txt`，受 `BUILD_PYTHON_BINDINGS=OFF` 门控：
`ctest -N` 实测 **Total Tests: 0**。真实测试面是 `examples/` 的示例程序。

发布 tarball 中 `third_party/{mbedtls,sqlite,winpcap}` 只有 README，因此上游自己
把 `CONFIG_IEC61850_R_GOOSE` / `CONFIG_IEC61850_R_SMV` 置 0，并关闭 tls/sntp/rsv/r_goose
示例与 `server_example_logging`。故 `BUILD_EXAMPLES=ON` 下 48 个示例目标中 39 个构建成功，
9 个按上游门控不参与构建（1 个 `iec61850_client_example_no_thread` 上游 `examples/CMakeLists.txt`
根本未引用）。

### 4. 消费者可见面
- 头文件安装到 `include/libiec61850/`（消费方式 `#include <libiec61850/xxx.h>`，与上游
  `libiec61850.pc` 的 `-I${includedir}` 一致）。
- `libiec61850.a` **不包含** HAL 对象，消费者必须同时链接 `hal`；
  `package_info().libs = ["iec61850", "hal"]`，`system_libs = ["pthread", "m", "rt"]`。
- 共享库 `libiec61850.so` 已静态并入 `hal-shared`，`shared=True` 时不额外暴露 hal。
- `package()` 按 `options.shared` 只保留一种 `libiec61850` 产物，并删除上游
  `share/pkgconfig/libiec61850.pc`（Conan 自行生成同名 .pc，避免冲突）。

### 5. 已知 API 陷阱（写进测试，避免后续消费者踩）
`LinkedList_destroy()` 实现为 `LinkedList_destroyDeep(self, Memory_free)`，
会对每个元素的 `data` 调 `free()`；若 `LinkedList_add()` 放入的是非堆指针，
退出期必然 segfault —— 本包 test_package 因此使用 `LinkedList_destroyStatic()`。

## 编译命令

```bash
cmake -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_EXAMPLES=ON -DBUILD_PYTHON_BINDINGS=OFF \
      -DCMAKE_INSTALL_PREFIX=<prefix> <src>
cmake --build . -j4
cmake --install . --prefix <prefix>
```

## Conan 配方

```bash
conan create archives/l/libiec61850/1.6.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
---

**编译结束**: 2026-09-26 14:11
**最终状态**: built
