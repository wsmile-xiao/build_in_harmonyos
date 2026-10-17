# blisp

## 简介

blisp（Bouffalo Labs ISP）是 PINE64 开发的开源 ISP（In-System Programming）工具和库，用于烧录 Bouffalo Lab RISC-V 系列 MCU，支持 BL602/BL604/BL702/BL704/BL706/BL808 等芯片。

## 功能概述

- **C 库 API**：`blisp_device_init()`、`blisp_device_open()`、`blisp_device_flash_write()`、`blisp_device_flash_erase()` 等
- **芯片支持**：BL60x、BL70x、BL808 系列
- **工具函数**：`crc32_calculate()`、`sleep_ms()`、`blisp_dlog()` 等
- **串口通信**：内置 vendored libserialport，无需系统安装

## OHOS 适配

### 适配要点

1. **子模块处理**：GitHub tag tarball 不含 git 子模块，在 conandata.yml 中额外声明 libserialport 源码，source() 中下载到 vendor/libserialport/
2. **禁用 CLI**：`BLISP_BUILD_CLI=OFF`，CLI 工具依赖 argtable3 子模块（tag tarball 不含），库本身不需要
3. **禁用上游测试**：`COMPILE_TESTS=OFF`，上游测试用 FetchContent 下载 GoogleTest，CI 可能无法访问
4. **CMake 兼容性补丁**：`write_file()` 替换为 `file(WRITE)`，修复新版 CMake 兼容性
5. **静态库**：package() 中删除共享库，只保留 `libblisp.a`

### 补丁

| 补丁 | 说明 |
|------|------|
| 0001-fix-cmake-write-file.patch | `write_file()` → `file(WRITE)`，修复 CMake 弃用命令 |
| 0002-fix-ohos-platform-detection.patch | `elseif(UNIX ...)` → `elseif(NOT WIN32 ...)`，修复 OHOS 平台检测 |

## 功能验证

```bash
# Conan 构建
conan create archives/b/blisp/0.0.5/ --build=missing

# test_package 输出
# PASS: crc32_calculate("123456789") = 0xCBF43926
# PASS: blisp_chip_bl60x.type = BLISP_CHIP_BL60X, type_str = "bl60x"
# PASS: blisp_chip_bl70x.type = BLISP_CHIP_BL70X, type_str = "bl70x"
# PASS: crc32_calculate("",0) = 0x00000000
# blisp 0.0.5: all 4 assertions passed
```

## 依赖

- 无外部 Conan 依赖（libserialport 以 vendored 源码形式内置）

## 参考

- 官方仓库：https://github.com/pine64/blisp
