# rtl-sdr 2.0.2 — 适配说明

## 这是什么

`rtl-sdr`（Osmocom 维护）把 **Realtek RTL2832U 的 DVB-T 电视棒**变成一个
软件无线电（SDR）接收机：`librtlsdr` 负责 USB 通信、调谐器驱动
（E4000 / FC0012 / FC0013 / FC2580 / R820T2）与 IQ 采样，上游同时给出
8 个命令行工具：

| 工具 | 作用 |
|---|---|
| `rtl_sdr` | 采样录制到文件 |
| `rtl_fm` | FM/AM/SSB 解调器 |
| `rtl_tcp` | rtl_tcp 协议的网络服务器（远程 SDR） |
| `rtl_test` | 设备自检 / 丢样统计（**需要真实电视棒**） |
| `rtl_eeprom` | 读写电视棒 EEPROM |
| `rtl_adsb` | ADS-B（1090 MHz）解码 |
| `rtl_power` | 频谱扫描（FFT 功率） |
| `rtl_biast` | 偏置电压控制 |

## 交付内容

```
include/rtl-sdr.h                    ← 唯一公共头（消费者入口）
include/rtl-sdr_export.h             ← generate_export_header 产出
lib/librtlsdr.so                     ← 未版本化实体文件，DT_SONAME=librtlsdr.so
lib/pkgconfig/librtlsdr.pc           ← prefix 已重写为 ${pcfiledir}/../..
bin/{rtl_sdr,rtl_fm,rtl_tcp,rtl_test,rtl_eeprom,rtl_adsb,rtl_power,rtl_biast}
licenses/COPYING                     ← GPL-2.0-or-later
```

依赖只有 **`libusb/1.0.27`**（上游唯一外部依赖；没有它 configure 阶段直接 FATAL）。

## 关键适配决策

### 1. 依赖发现必须走 pkg-config

上游根 `CMakeLists.txt`：

```cmake
pkg_check_modules(LIBUSB libusb-1.0 IMPORTED_TARGET)
...
if(PKG_CONFIG_FOUND AND NOT LIBUSB_FOUND)
    message(FATAL_ERROR "LibUSB 1.0 required to compile rtl-sdr")
endif()
```

conan 的 CMakeDeps 不会生成 `.pc`，所以 `generate()` 里再加一个
`PkgConfigDeps(self)`：按 libusb 包的 `pkg_config_name`（`libusb-1.0`）生成
`libusb-1.0.pc` 到 generators 目录，并把该目录放进 `PKG_CONFIG_PATH`
（仓库 `rpm/6.0.2` 同款先例）。CMake 日志中可见
`Found libusb-1.0, version 1.0.27` —— 确认命中的是 conan 包的 .pc。

### 2. OHOS 是 CMake 未知平台 → 必须自己补 SONAME

`CMAKE_SYSTEM_NAME=HarmonyOS` 没有 `Platform/HarmonyOS.cmake`，于是
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空：共享库不带 `DT_SONAME`
（CI **L5a** 门禁必挂），同时 install 会尝试创建版本化符号链接
（HMDFS 建链不可靠，`libsoci`/`expat` 都因此返工过）。

处理（`hidapi/0.15.0` 同款）：

```python
toolchain.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
```

实测产物（本机原生构建 + `readelf -d`）：

```
librtlsdr.so: (SONAME) librtlsdr.so
              (NEEDED) libusb-1.0.so.0, libc.so.6      ← 无绝对/相对路径（L5b）
```

### 3. 剔除上游不可重定位的 CMake export 与 udev 规则

* 上游 `install(EXPORT RTLSDR-export)` 生成的 `rtlsdrTargets.cmake` 里
  `INTERFACE_INCLUDE_DIRECTORIES` / `INTERFACE_LINK_LIBRARIES` 是**构建机**上
  libusb 的绝对路径（conan 缓存路径），并且导出的是与被删除文件同名的静态库
  → `package()` 里整个 `lib/cmake/` 删除。消费者用 conan CMakeDeps 的
  `rtlsdr::rtlsdr`（`cmake_file_name=rtlsdr`）或包内 `.pc`。
* `INSTALL_UDEV_RULES=OFF`（udev 规则属系统集成，不进 conan 包），
  `package()` 里再防御性清掉 `etc/`。
* `librtlsdr.pc` 的 `prefix`（= 包绝对路径）与 `Cflags`/`Libs.private` 里的
  构建机 libusb `-I/-L` 路径统一改写成 `${pcfiledir}/../..` 相对形式
  ——上游只在 `CMAKE_CROSSCOMPILING` 时才 unset 它们，而 CI 是原生构建，清不掉。

### 4. CLI 申报（commands.json）放在**版本目录**，且不显式写 bindirs

本包交付 8 个 CLI，R38 要求申报 `commands.json`。本仓存在两条互斥口径：

* CI **L0k** / preflight **PF8**：只有 conanfile 里出现
  `package_type = "application"` 或非空 `cpp_info.bindirs = [...]` 时才要求
  `commands.json`，且只认**包级目录** `archives/<字母>/<包>/commands.json`；
* preflight **PF9**：变更路径必须落在 `archives/<字母>/<包>/<版本>/` 之下，
  包级目录的文件会被判「缺版本目录层」硬拦。

因此本包按仓库现有先例（`archives/d/d0-blind-id/1.0/commands.json`、
`kor/0.6.8`、`aggdraw/1.4.1`、`libtool/2.5.4.1` 等 8 例）把 `commands.json`
放在 **`archives/r/rtl-sdr/2.0.2/commands.json`**，并**不显式声明**
`cpp_info.bindirs`（conan 的默认 bindirs 本来就是 `bin`，8 个工具照常随包交付并
由 conanrun/CMakeDeps 导出）——这样 L0k 走「库包，命令行为可选」分支、
PF8 与 PF9 同时保持绿色。

### 5. 上游版本号 quirk（保留，不改源码）

tag 是 `v2.0.2`，但根 `CMakeLists.txt` 里 `VERSION_INFO_PATCH_VERSION` 仍是
`1` → 构建出的 `VERSION`/`LIBVER`、`.pc` 的 `Version:` 与
`rtlsdrConfigVersion.cmake` 都自报 **2.0.1**（CMake 配置阶段打印
`Building for version: 2.0.1 / 2.0.1`）。包版本按 tag 记为 `2.0.2`，该 quirk 不
改上游源码。

### 6. 唯一的源码补丁：OHOS/musl 没有 `pthread_cancel()`

`patches/0001-ohos-portable-demod-thread-exit.patch` —— 只改 `src/rtl_adsb.c`
的**进程退出路径**一行（`src/librtlsdr.c` 等库本体不动）。

**CI #65385 实证**（worker CI-024，26 s）：

```
[100%] 其它 7 个工具全部链接成功
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by rtl_adsb.c
>>>               CMakeFiles/rtl_adsb.dir/rtl_adsb.c.obj:(main)
clang-15: error: linker command failed with exit code 1
```

OHOS 的 libc 是 musl：**没有 `pthread_cancel` 这个符号**（编译期只报
`-Wimplicit-function-declaration` 警告，链接期才爆）。8 个工具里只有
`rtl_adsb` 用它。

上游原逻辑：`rtlsdr_read_async()` 返回后，若 `do_exit == 0`（库错误路径，不是
Ctrl-C），demod 线程仍阻塞在 `pthread_cond_wait(&ready)` 上，所以用
`pthread_cancel()` 强杀再 `pthread_join()`。而该线程**本来就有自己的退出
条件**（`while (!do_exit)`，信号处理函数里的同一个标志），因此补丁改成：

```c
	rtlsdr_cancel_async(dev);
-	pthread_cancel(demod_thread);
+	do_exit = 1;
+	safe_cond_signal(&ready, &ready_m);
	pthread_join(demod_thread, NULL);
```

线程被唤醒 → 循环条件为假 → 退出循环 → `rtlsdr_cancel_async()` → 返回 → `join`
成功。既覆盖 Ctrl-C 路径也覆盖库错误路径，**语义与 `pthread_cancel` 等价且无
线程泄漏**，在 musl 与 glibc 上都成立。

本机验证：

* 补丁用 conan 同款 `patch_ng` 对上游 tarball 实测应用成功（`strip=0`/`1` 均可）；
* `gcc -fsyntax-only -Wall` 编译补丁后的 `rtl_adsb.c`：**通过，无新增警告**；
* 退出路径语义单测（复刻同一份 cond_wait 循环 + `do_exit` + 唤醒 + `join`，
  10 s 超时兜底）：`pthread_join` 正常返回，`OK`。

## 测试证据（平台 rule12）

### ① 上游测试：**没有**（如实声明）

顶层 `CMakeLists.txt` 没有 `enable_testing()`/`add_test`，`src/` 也没有测试目标；
`rtl_test` 是需要真实 RTL2832U 电视棒的硬件自检程序 —— CI 与开发机都没有该硬件
（设备枚举恒为 0），不能当测试用。

### ② build() 内的 CLI 启动冒烟（真执行交付的可执行文件）

8 个工具无参运行必须在秒级退出并给出输出，否则 `build()` 抛异常：

```
HMBS_CLI_SMOKE rtl_sdr    bytes=469   ← usage 全文
HMBS_CLI_SMOKE rtl_fm     bytes=28    ← "No supported devices found."
HMBS_CLI_SMOKE rtl_tcp    bytes=28
HMBS_CLI_SMOKE rtl_test   bytes=28
HMBS_CLI_SMOKE rtl_eeprom bytes=28
HMBS_CLI_SMOKE rtl_adsb   bytes=28
HMBS_CLI_SMOKE rtl_power  bytes=29
HMBS_CLI_SMOKE rtl_biast  bytes=28
```

### ③ 完整消费者用例（端到端业务流程，14 项）

`test_package/test_rtlsdr.c` **只**链接交付的 `librtlsdr.so` + `<rtl-sdr.h>`。
没有电视棒，所以用 **ELF 符号介入**在进程内造一台：

```
可执行文件 ENABLE_EXPORTS(-Wl,--export-dynamic)
  → 自身符号进入动态符号表
librtlsdr.so 调用的 libusb_* ▼
  libusb_init / get_device_list(返回 1 个假 device) / get_device_descriptor
  (idVendor=0x0bda, idProduct=0x2838, iManufacturer=1, iProduct=2, iSerialNumber=3)
  / free_device_list / exit / open / close / get_device
  / get_string_descriptor_ascii(1..3 → “FakeVendor Inc.” / “Fake RTL2832U Dongle” / “FAKESERIAL0001”)
上层的 rtlsdr_* 公开 API、机型表匹配、索引遍历、序列号反查、错误路径全部是库自己的代码
```

核对结果（逐项显式比对，无 `assert` 宏）：

1. `rtlsdr_get_device_count()` == 1；
2. `rtlsdr_get_device_name(0)` == `Generic RTL2832U OEM`（注入的 VID/PID 命中上游机型表）；
3. `rtlsdr_get_device_usb_strings(0, ...)` == 0，且厂商/产品/序列号三串与设备侧注入逐字节一致；
4. `rtlsdr_get_index_by_serial("FAKESERIAL0001")` == 0，未知序列号 == -3；
5. 越界路径：`rtlsdr_get_device_name(9)` 回退到最后一个匹配机型名（上游实现如此）、
   `rtlsdr_get_device_usb_strings(9, ...)` 不触碰输出缓冲区（哨兵值验证）、
   `rtlsdr_open(&dev, 9)` 返回非 0 且 `dev` 仍为 NULL；
6. 设备侧计数（`get_device_list=10`、描述符 13 次、字符串描述符 5 次、`open=3`）
   证明请求真的穿过了介入层。

```
设备侧计数：get_device_list=10 描述符=13 字符串描述符=5 open=3
rtlsdr 消费者用例结果：14 项检查，0 项失败
```

> 顺带记录一个上游缺陷：`rtlsdr_get_device_usb_strings()` 开头的
> `r = libusb_init(&ctx)` 覆盖了默认的 `-2`，越界索引时既不报错也不写缓冲区
> （返回 0），调用方无法区分成功与越界 → 用例按“缓冲区不被触碰”断言。

### ④ 适配自检（M = 23 条，非上游用例）

`test_package/test_layout.py`：库是 ELF `ET_DYN` 且 `DT_SONAME` 相对（纯 Python
解析 `.dynamic`，不依赖 `readelf`）、`lib/` 只留一份库、公共头齐全、8 个 CLI
可执行、`.pc` 可重定位且无构建机路径、GPL COPYING、未带上游 `lib/cmake/rtlsdr`、
无构建中间产物与隐藏文件。实测 23/23。

## 版本与来源

* 上游 tag：`v2.0.2`（<https://github.com/osmocom/rtl-sdr>）
* tarball：`https://github.com/osmocom/rtl-sdr/archive/refs/tags/v2.0.2.tar.gz`
* sha256：`d69943eb32df742bc38a00ce6615e41250fd57851174e5ff916ec31e9e9e68e9`（136512 字节）
* 下载双校验：sha256 一致 + `tar tzf | wc -l` = 92
* 许可：GPL-2.0-or-later（`COPYING` 随包交付）

## 本地验证范围（诚实声明）

本机没有 OHOS 工具链，验证分两层：

1. **原生复现（已做）**：`cmake -S <src> -B build -DDETACH_KERNEL_DRIVER=ON
   -DINSTALL_UDEV_RULES=OFF -DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,
   -DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 构建 + 安装，消费者用例编译运行
   14/14，`test_layout.py` 23/23，`readelf` 确认 SONAME/NEEDED 相对、
   安装产物无 RPATH/RUNPATH。
2. **conan 全流程（已做，Linux x86_64）**：用本机 libusb 头/库临时包一个
   `libusb/1.0.27`（`package_info` 与仓库内该包一致），在隔离的
   `CONAN_HOME` 下 `conan create` 整条配方：`generate()` 的 PkgConfigDeps +
   `PKG_CONFIG_PATH` 生效（CMake 打印 `Found libusb-1.0, version 1.0.27`）、
   `build()` 冒烟 8/8、`package()` 重写 .pc 并剔除 `.a`/`lib/cmake`、
   `test_package` 编译 + 用例 14/14 + 自检 23/23，全部通过。
   （源码用本地 tarball 通过 `file://` 提供，因为实验期间 GitHub 直连超时；
   已用 sha256 校验同一份归档。）
3. **未在本机验证**：OHOS clang 交叉/原生工具链下的真实构建、CI 的 L0/L1/L5
   门禁实跑（本机没有鸿蒙 SDK 与设备）。这些只能在平台 CI 上确认。
   CI #65385 已确认配方主体可用：L0/L0m/L0n 门禁全绿、CMake configure 全绿、
   `Found Threads: TRUE`、`Found libusb-1.0, version 1.0.27`、7/8 个工具链接成功；
   唯一失败是 musl 缺 `pthread_cancel`（见第 6 节的补丁）。该补丁已在本机用
   `patch_ng` 应用 + `gcc -fsyntax-only -Wall` + 退出路径语义单测验证。
