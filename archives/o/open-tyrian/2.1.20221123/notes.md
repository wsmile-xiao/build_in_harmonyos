# open-tyrian 2.1.20221123 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-04
- 平台: OpenHarmony aarch64
- 编译器: clang 15
- 源码: https://github.com/opentyrian/opentyrian/archive/refs/tags/v2.1.20221123.tar.gz

## 依赖
- sdl2/2.30.10 (Conan 制品仓，静态库)
- sdl2_net/2.2.0 (Conan 制品仓，静态库)

## 适配过程

### 编译
OpenTyrian 使用纯 Makefile 构建，无需 configure 步骤。

```bash
# 设置环境
export CC=clang
export CFLAGS="-fPIC -O2 -pedantic -Wall -Wextra -Wno-missing-field-initializers"
export PKG_CONFIG_PATH="<conan_pkgconfig_path>"

# 构建
make -j2 VCS_IDREV="echo v2.1.20221123"

# 安装
make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX INSTALL=cp INSTALL_PROGRAM=cp INSTALL_DATA=cp
```

### 注意事项
1. **VCS_IDREV**: Makefile 默认使用 `git describe --tags` 获取版本号，源码非 git 仓库时需手动设置 `VCS_IDREV`
2. **INSTALL 命令**: OHOS 平台无 `install` 命令，需用 `INSTALL=cp` 替代
3. **-Wno-format-truncation**: GCC 专用警告选项，clang 不识别（仅警告，不影响编译）
4. **SDL2/SDL2_net .pc 文件**: SDL2 的 Conan 包提供 .pc 文件但路径指向 `/`；SDL2_net 不提供 .pc 文件（使用 CMake targets）。需手动创建/修正 .pc 文件

### 上游测试
- 无上游测试（游戏项目，无 tests/ 目录，无 make check/test 目标）

### 产物
- 可执行文件: opentyrian (ELF 64-bit aarch64, 动态链接)
- 辅助文件: man page, desktop file, 图标

## 结论
编译成功，无需源码修改。OHOS 平台原生支持，无需平台适配补丁。
---

**编译结束**: 2026-09-04 01:43
**最终状态**: built
