# blisp 0.0.5 适配笔记

## 软件简介

blisp（Bouffalo Labs ISP）是 PINE64 开发的开源工具和库，用于烧录 Bouffalo Lab RISC-V 系列 MCU（BL602/BL604/BL702/BL704/BL706/BL808）。提供 `libblisp` C 库和可选的 `blisp` 命令行工具。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-14
- 编译器: clang / clang++ (OHOS aarch64)
- Conan 版本: 2.29.1
- Python 版本: 3.12.9
- 状态: built（CI 已在真实鸿蒙 worker #007 通过，构建 #2451）

## 源码与依赖

### 主源码

| 项目 | 内容 |
|------|------|
| 源码 URL | https://github.com/pine64/blisp/archive/refs/tags/v0.0.5.tar.gz |
| sha256 | 79f87fbbb66f1d9ddf250cdc15dc16638d95e0905665003b08920a4b1fda9f96 |
| 解压根目录 | blisp-0.0.5 |
| 许可证 | MIT |

### 子模块依赖

blisp 的 `.gitmodules` 声明了两个子模块：

| 子模块 | 路径 | 用途 | 是否需要 |
|--------|------|------|----------|
| libserialport | vendor/libserialport | 核心库串口通信 | **需要** — CMakeLists.txt 在 Linux 下直接编译其源码 |
| argtable3 | vendor/argtable3 | CLI 工具参数解析 | **不需要** — 禁用 BLISP_BUILD_CLI 后无需 |

**关键问题**：GitHub tag tarball 不含 git 子模块内容，`vendor/libserialport/` 目录为空。CMakeLists.txt 在 `BLISP_USE_SYSTEM_LIBRARIES=OFF`（默认）时直接编译 `vendor/libserialport/` 下的 `serialport.c`、`timing.c`、`linux.c`、`linux_termios.c`，因此必须在 source() 中额外下载 libserialport 源码。

### libserialport 源码

| 项目 | 内容 |
|------|------|
| 源码 URL | https://github.com/sigrokproject/libserialport/archive/6f9b03e597ea7200eb616a4e410add3dd1690cb1.tar.gz |
| sha256 | 9cec0af2dddd35714cc796e018f9231c796d61a152a379862641a00e0b01f77b |
| 对应 commit | 6f9b03e597ea7200eb616a4e410add3dd1690cb1（blisp v0.0.5 子模块指针） |
| 解压目标 | vendor/libserialport/ |

## 构建配置

```python
# conanfile.py generate() 关键配置
tc.variables["BLISP_BUILD_CLI"] = False         # 禁用 CLI 工具（避免 argtable3 子模块依赖）
tc.variables["COMPILE_TESTS"] = False           # 禁用上游测试（避免 FetchContent 下载 GoogleTest）
tc.variables["BLISP_USE_SYSTEM_LIBRARIES"] = False  # 使用 vendored libserialport 源码
```

### 选项取舍依据

| 选项 | 取值 | 依据 |
|------|------|------|
| BLISP_BUILD_CLI | False | CLI 工具依赖 argtable3 子模块，tag tarball 不含该子模块；库本身不需要 |
| COMPILE_TESTS | False | 上游测试用 FetchContent 从 GitHub 下载 GoogleTest v1.17.0，CI 环境可能无法访问外部仓库；L1 由 test_package 承担 |
| BLISP_USE_SYSTEM_LIBRARIES | False | OHOS 上无预装 libserialport，使用 vendored 源码构建 |

## 产物处理

CMakeLists.txt 同时构建共享库 `libblisp.so` 和静态库 `libblisp.a`，install 时两者都安装到 `lib/`。为避免 .so 污染，在 `package()` 中删除共享库，只保留静态库 `libblisp.a`。

安装的公共头文件（5 个）：
- `blisp.h` — 主 API（设备初始化、烧录、擦除等）
- `blisp_easy.h` — 易用封装
- `blisp_chip.h` — 芯片类型定义和描述符
- `blisp_struct.h` — 数据结构
- `blisp_util.h` — 工具函数（CRC32、日志、延时）

## 补丁说明

### 0001-fix-cmake-write-file.patch

CMakeLists.txt 在 Linux 分支中调用 `write_file()` 写入 `vendor/libserialport/config.h`：

```cmake
write_file(${CMAKE_SOURCE_DIR}/vendor/libserialport/config.h "// bypass errors.")
```

`write_file` 是 CMake 2.x 命令，自 CMake 3.0 起标记为弃用。补丁将其替换为等效的 `file(WRITE ...)`（注意：`write_file` 会自动追加换行，`file(WRITE)` 不会，故显式补上 `\n`）：

```cmake
file(WRITE ${CMAKE_SOURCE_DIR}/vendor/libserialport/config.h "// bypass errors.\n")
```

### 0002-fix-ohos-platform-detection.patch

CMakeLists.txt 用 `elseif(UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")` 检测 Linux 分支，但 OHOS 的 `CMAKE_SYSTEM_NAME` 非 "Linux" 且 `UNIX` 为 false，导致该分支不匹配。而 `__linux__` 宏仍存在，`libserialport_internal.h` 仍 `#include "linux_termios.h"`，`SP_PRIV` 宏却从未被 CMake 定义，导致 "unknown type name 'SP_PRIV'" 编译错误。

补丁将 `UNIX` 改为 `NOT WIN32`，不依赖 `CMAKE_SYSTEM_NAME` 具体值，让所有非 Windows/非 Apple/非 FreeBSD 平台（含 OHOS）走 Linux 分支：

```cmake
# 修改前
elseif(UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")
# 修改后
elseif(NOT WIN32 AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")
```

## test_package 验证

test_package 链接 `libblisp.a` 并调用其公开 C API：

1. **CRC32 标准测试向量**：`crc32_calculate("123456789", 9)` == `0xCBF43926`
   - 这是 CRC32（多项式 0x04C11DB7，反射，XorIn/XorOut=0xFFFFFFFF）的标准检查值
   - `crc32_calculate` 实现：初始 0xFFFFFFFF，处理后 XOR 0xFFFFFFFF
2. **空缓冲区 CRC32**：`crc32_calculate("", 0)` == `0x00000000`
   - 空输入不进入循环，直接 0xFFFFFFFF ^ 0xFFFFFFFF = 0
3. **BL60X 芯片描述符**：`blisp_chip_bl60x.type == BLISP_CHIP_BL60X`
4. **BL70X 芯片描述符**：`blisp_chip_bl70x.type == BLISP_CHIP_BL70X`

这些测试不需要真实硬件，适合 CI 环境。CRC32 验证了算法正确性，芯片描述符验证了符号链接和数据初始化。

## 本地测试记录

上游测试（`COMPILE_TESTS`）使用 `FetchContent` 从 GitHub 下载 GoogleTest v1.17.0，CI 环境无法访问外部仓库，故配方中将其禁用（`upstream_test_in_build: false`）。为弥补上游测试缺失，在本地对 test_package 进行了验证。

### 运行环境

| 项目 | 内容 |
|------|------|
| 构建系统 | CMake（同 CI 配方） |
| 测试程序 | test_package/test_blisp.c（消费者视角 smoke test） |
| 断言数量 | 4 |

### 测试结果

test_blisp 本地运行全部通过，输出如下：

```
PASS: crc32_calculate("123456789") = 0xCBF43926
PASS: blisp_chip_bl60x.type = BLISP_CHIP_BL60X, type_str = "bl60x"
PASS: blisp_chip_bl70x.type = BLISP_CHIP_BL70X, type_str = "bl70x"
PASS: crc32_calculate("",0) = 0x00000000
blisp 0.0.5: all 4 assertions passed
```

| # | 断言 | 期望值 | 结果 |
|---|------|--------|------|
| 1 | `crc32_calculate("123456789", 9)` | 0xCBF43926 | PASS |
| 2 | `blisp_chip_bl60x.type == BLISP_CHIP_BL60X` | 符号链接正确 | PASS |
| 3 | `blisp_chip_bl70x.type == BLISP_CHIP_BL70X` | 符号链接正确 | PASS |
| 4 | `crc32_calculate("", 0)` | 0x00000000 | PASS |

4 项断言全部通过，验证了 CRC32 算法实现正确性、芯片描述符符号链接与数据初始化正确性。由于上游 GoogleTest 测试无法在 CI 运行，本次本地验证作为 L1 质量补充。

## 交付物

| 文件 | 说明 |
|------|------|
| libblisp.a | 静态库（ISP 烧录核心 + vendored libserialport） |
| blisp.h | 主 API 头文件 |
| blisp_easy.h | 易用封装头文件 |
| blisp_chip.h | 芯片类型定义头文件 |
| blisp_struct.h | 数据结构头文件 |
| blisp_util.h | 工具函数头文件 |

---

**编译日期**: 2026-07-14
**Conan 引用**: `blisp/0.0.5`
