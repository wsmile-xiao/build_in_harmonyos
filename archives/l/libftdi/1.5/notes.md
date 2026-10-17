# libftdi 1.5 OHOS 适配笔记

日期：2026-09-17　分支：feat/libftdi-1.5　目标：ohos-aarch64 (OHOS 6.0, clang 15, armv8)

## 上游信息

- 官方源码：https://www.intra2net.com/en/developer/libftdi/download/libftdi1-1.5.tar.bz2
- sha256：`7c7091e9c86196148bd41177b4590dccb1510bfe6cea5bf7407ff194482eb049`（本地实测一致）
- 许可证：核心库 LGPL-2.1-or-later（COPYING.LIB）；ftdi_eeprom 工具 GPL-2.0-or-later（未构建）
- 构建：CMake（根 CMakeLists.txt，250 行）
- 依赖：libusb-1.0（必需，FindUSB1.cmake）；libconfuse（仅 ftdi_eeprom）；Boost unit_test_framework（仅 test/）

## 环境事实

- 工具链：clang 15.0.4 wrapper（自动带 `--sysroot` + `-Wl,--code-sign`），位于 `$HOME/usr/local/bin`；
  profile 的 `/data/service/hnp/bin/clang` 在本机不存在 → recipe 用 libxext 模式在 generate()
  后修补 conan_toolchain.cmake（toolchain 的 `set()` 会覆盖命令行 -D，必须在文件层面替换）。
- CMake 4.1.2：无 Platform/HarmonyOS 模块（见下方根因）。
- libusb/1.0.27（ohpcd，含 OHOS 内核补丁）缓存可用：包 ID `01d92cf…71517f`（shared=True）。
- libconfuse：仓库有 3.3 recipe 但无可用包（本地 0、远端无）→ 禁用 FTDI_EEPROM。
- 未签名二进制在本机可直接运行（`-Wl,--code-sign` 由 clang wrapper 注入），无需 binary-sign-tool。

## 根因记录（知识库查重结论：路径 A，全部复用既有条目，未新增 DRAFT）

### CMake 无 Platform/HarmonyOS 模块的连锁反应（3 个独立表现）

`CMAKE_SYSTEM_NAME=HarmonyOS` 在 CMake 4.1 中无对应 Platform 模块，导致：

1. **UNIX 变量未定义** → 上游 `if(${UNIX})` 不成立 → `libdir`/`LIBFTDI_LIBRARY_DIRS` 为空 →
   `configure_package_config_file` 直接报 "Variable LIBFTDI_LIBRARY_DIRS does not exist"。
   （注意 `if(${UNIX})` 在 UNIX 为空时会展开成 `if()` 语法错误，patch 改为 `if(UNIX OR …)`。）
   → **已被 E532 覆盖**（"上游 CMake if(WIN32) elseif(UNIX) else() 平台三分支不识别 HarmonyOS"），
   修复模式一致：`OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`。本次不新增条目。
2. **`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 未定义** → 链接命令无 `-Wl,-soname,` → 产出的
   libftdi1.so **没有 DT_SONAME**（CI L5a 门禁必挂）。解法：toolchain
   `cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`。
   → **已被 DRAFT-libharu-2.3.0-missing-dt-soname 覆盖**（同方案）；区别仅 libftdi 上游
   已设 SOVERSION/VERSION，无需上游 patch，只需注入 flag。本次不新增条目。
3. CMakeCache 会有 "System is unknown to cmake" 警告，不影响结果（DRAFT-nng 亦有记录）。

硬件不存在 / USB 测试不能离线运行本身不算知识库创新，按约定不立条。

### 上游构建系统细节

- `src/CMakeLists.txt`：`add_library(ftdi1 SHARED …)` **硬编码 SHARED**；STATICLIBS=ON 只会
  额外加一个 `ftdi1-static` 目标（两种都构建、都安装）。Conan 的 shared=False 需要只产出
  .a → patch 新增 `DONT_BUILD_SHARED` 开关切换 `LIBFTDI_LIBRARY_TYPE`。
- `cmake/FindUSB1.cmake` 消费经典模块变量 `LIBUSB_INCLUDE_DIR` / `LIBUSB_LIBRARIES`
  （pkg-config 或显式变量）。CMakeDeps 生成的 USB1-config.cmake 只定义 `USB1_INCLUDE_DIRS`
  等名字 → 用 `cmake_extra_variables` 属性把 conan 值暴露为上游要的变量名。
- `cmake_minimum_required(VERSION 2.6 FATAL_ERROR)`：CMake 4.x 拒绝 <3.5，
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` 可不改源码通过。
- ftdi.h 非自包含（`#include <libusb.h>` 并使用其常量）→ `cpp_info.requires = ["libusb::libusb"]`
  传递头文件路径；上游安装到 `include/libftdi1/ftdi.h`（带前缀，消费侧 `#include <libftdi1/ftdi.h>`）。

## 上游测试边界（如实分类，不伪造）

- `test/basic.cpp`：`ftdi_new()` → `ftdi_init()` → `libusb_init(NULL)`。沙箱无 USB 子系统，
  实测返回 -1 (LIBUSB_ERROR_IO) → **hardware-environment，不可离线运行**。
- `test/baudrate.cpp`：fixture 同样依赖 `ftdi_new()`，但被测计算 `ftdi_convert_baudrate`
  是**纯函数**（只用 `ftdi->type`，不碰 USB 状态）。上游为单测导出了包装函数
  `convert_baudrate_UT_export`（ftdi.c 内 `static int ftdi_convert_baudrate` 的导出口）。
  其官方向量表为 C++ map 字面量（键是运行时整数表达式 `BASE*16/(2*16+N)` 与 ±1）。
  → **离线复用**：test_package 逐类复刻向量（TYPE_AM 24 / BM·2232C·R·230X 各 28 /
  2232H·4232H·232H 各 29，共 284 条），断言语义与上游 BOOST_CHECK_EQUAL×4 完全一致
  （actual_baudrate、divisor、fractional_bits、clock 四元组），全部通过。
- 上游 `test/` 需 `find_package(Boost COMPONENTS unit_test_framework REQUIRED)`，
  无 Boost UTF 时 configure 直接失败 → 不复用上游 test/ 目录，test_package 自写纯计算测试。

## 构建结果（conan create，OHOS profile，Release）

- recipe revision `5793059f4e052359731d31458d7121af`
- shared=True：包 ID `8b90efacddbc4e0de5986c54badcb6feb43da809` — lib/libftdi1.so(.2/.2.5.0)
  - readelf：ELF64 / AArch64；SONAME `libftdi1.so.2`；NEEDED `libusb-1.0.so.0`、`libc.so`；无 RPATH/RUNPATH
- shared=False：包 ID `eb099f95f7fe600de671f5b18336d91ea4efcb3a` — lib/libftdi1.a（无 .so 残留）
  - consumer：NEEDED `libusb-1.0.so.0`、`libc.so`（libusb 为 shared 依赖，闭包正确）
- 两变体 test_package 均真实运行：284 官方向量 + 版本/错误路径/NULL 安全 + ELF 审计全过。

## 消费者注意

- 上游 libftdi1.pc.in 用 `@prefix@` 硬编码构建路径 → recipe 的 package() 用包目录绝对路径
  重写 `lib/pkgconfig/libftdi1.pc`（Requires: libusb-1.0）。
- CMake 消费者用 `find_package(libftdi1)` + `libftdi1::libftdi1`（与上游 config 模块名一致）。
- `ftdi_eeprom` 工具未构建（libconfuse 不可用）；如后续需要，先做 libconfuse 包。
