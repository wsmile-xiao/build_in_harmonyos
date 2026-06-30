# FreeImage 3.18.0 适配笔记

## 编译环境
- 构建系统: makefile（Makefile.gnu）
- 编译日期: 2026-06-24
- 编译器: clang/clang++ 15.0
- 架构: aarch64
- 状态: published
- 功能测试: ✅ 通过（20/20）

## 编译步骤

```bash
# 1. 加载编译上下文
source .build-context-freeimage-3.18.0

# 2. 使用 Makefile.gnu 构建
cd $BUILD_SRC_DIR
make -f Makefile.gnu -j1

# 3. 安装到暂存区（DESTDIR 模式）
make -f Makefile.gnu install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 4. 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package freeimage 3.18.0

# 5. 安装到本地（模拟用户部署）
make -f Makefile.gnu install PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| 序号 | 问题描述 | 根本原因 | 解决方案 |
|------|---------|---------|---------|
| 1 | 缺少 `install` 命令 | 鸿蒙系统没有 GNU `install` 工具 | 在 Makefile.gnu 中用 `mkdir -p`/`cp`/`chmod` 替代 |
| 2 | PNG ARM NEON 未定义符号 | 内嵌 libPNG 在 aarch64 上自动启用 NEON 优化，但未包含 arm/ 实现目录 | 在 CFLAGS 中添加 `-DPNG_ARM_NEON_OPT=0` 禁用 NEON 优化 |
| 3 | install -o root -g root 失败 | 鸿蒙系统无 root 用户 | 移除安装目标中的用户和组归属参数 |
| 4 | ln -sf 在 HMDFS 上失败 | HMDFS 不支持覆盖式创建符号链接 | 改用 `rm -f && ln -s` 模式创建符号链接 |

## 源码修改

### Makefile.gnu（已追踪，生成补丁 0001-Makefile.gnu.patch）

修改内容：
1. 新增 `PREFIX ?= /usr` 变量，支持可配置安装前缀
2. 将 `INCDIR`/`INSTALLDIR` 改为 `$(DESTDIR)$(PREFIX)/...` 路径模式（兼容 DESTDIR 模式）
3. 将 `install` 命令替换为 `mkdir -p`/`cp`/`chmod`（鸿蒙系统无 `install` 命令）
4. 移除 `-o root -g root` 用户归属参数
5. 将 `ln -sf` 改为 `rm -f && ln -s` 以兼容 HMDFS 文件系统
6. 在 CFLAGS 中添加 `-DPNG_ARM_NEON_OPT=0`（禁用内嵌 libPNG 的 ARM NEON 优化）

## 依赖版本

FreeImage 3.18.0 内嵌所有依赖，无需外部库：
- libJPEG 9a
- libPNG 1.6.24
- libTIFF 4.0.6
- zlib 1.2.8
- OpenJPEG 2.1.0
- OpenEXR 2.2.0
- LibRaw 0.17.2
- LibWebP 0.5.0
- LibJXR 1.0

## 功能验证结果（✅ 全部通过）

在鸿蒙设备上实际运行功能测试程序，覆盖 20 项核心 API 测试：

| 测试类别 | 测试项目 | 结果 |
|---------|---------|------|
| 基础功能 | 库初始化与版本查询 | ✅ |
| 基础功能 | 图像创建与像素绘制 | ✅ |
| 格式读写 | BMP 保存/加载 | ✅ |
| 格式读写 | PNG 保存/加载 | ✅ |
| 格式读写 | JPEG 保存/加载 | ✅ |
| 格式读写 | TIFF 保存/加载 | ✅ |
| 图像处理 | 色彩深度转换（24→32/8 位） | ✅ |
| 图像处理 | 图像缩放（双三次重采样） | ✅ |
| 图像处理 | 图像旋转 90° | ✅ |
| 图像处理 | 水平翻转 | ✅ |
| 图像处理 | 伽马校正 | ✅ |
| 其他 | 调色板操作、多格式批量保存 | ✅ |

**动态链接测试**: 编译成功，运行时正确加载 libfreeimage-3.18.0.so
**静态链接**: 上游已知问题（b44ExpLogTable main 符号冲突），建议使用动态库

测试程序源码: `reports/freeimage_func_test.c`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| freeimage-3.18.0-ohos-aarch64.tar.gz | 33.8 MB | 预编译包（含动态库 + 静态库 + 头文件） |
| freeimage-3.18.0-ohos-aarch64-debug.tar.gz | 1.2 MB | 调试符号包 |
| 0001-Makefile.gnu.patch | ~1KB | 鸿蒙平台适配补丁 |
| freeimage_func_test.c | ~6KB | 功能测试程序源码 |

## 注意事项

- PNG ARM NEON 优化已禁用（-DPNG_ARM_NEON_OPT=0），回退为 C 实现，安全可靠
- 内嵌库（LibJXR、LibWebP）的编译告警为上游源码原有问题，非致命
- 静态库包含构建工具的 main 函数（b44ExpLogTable），静态链接时需加 `-Wl,--allow-multiple-definition`
- 建议优先使用动态库（libfreeimage-3.18.0.so）
---

**编译结束**: 2026-06-24 12:06
**功能测试**: 2026-06-24 14:55（20/20 通过）
**最终状态**: published
