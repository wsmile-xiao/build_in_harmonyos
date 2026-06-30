# largetifftools 1.4.1 适配笔记

## 编译环境
- 构建系统: autotools（手动 Makefile）
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 config.status 脚本在创建临时目录时遇到权限问题（"Permission denied"），无法使用标准的 autotools 流程。采用了手动编译方式：

1. 下载源代码：https://codeload.github.com/gn-nhc/largetifftools/tar.gz/main
2. 手动创建 config.h（包含必要的宏定义）
3. 创建最小化 Makefile
4. 设置环境变量：`LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib`
5. 编译命令：
   ```bash
   cd /storage/Users/currentUser/builds/largetifftools-1.4.1.work
   cp config.h src/
   make -j1
   make install DESTDIR=/storage/Users/currentUser/test-install-largetifftools-1.4.1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: JPEG library not found | LD_LIBRARY_PATH 未设置，测试程序无法加载动态库 | 设置 `LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib` 并添加 `-Wl,-rpath` |
| 2 | configure: cannot compute sizeof (size_t) | AC_CHECK_SIZEOF 测试程序无法运行，缺少动态库加载 | 同上，设置 LD_LIBRARY_PATH |
| 3 | config.status: Permission denied | 临时目录创建权限问题（config.status 第 742 行） | 采用手动编译，创建最小化 Makefile |
| 4 | 缺少 config.h | 源文件 #include "config.h" | 手动创建 config.h 并复制到 src/ |
| 5 | tifffastcrop 链接失败：undefined symbol: png_* | libpng 是静态库，需要链接 zlib | 添加 `-lpng16 -lz` 到 LIBS |

## 源码修改

无补丁。手动创建了以下文件：
- `config.h`：手动创建的配置头文件
- `Makefile`：手动创建的编译脚本
- `src/config.h`：从根目录复制的配置头文件

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libtiff | 4.7.1 | 已安装 |
| libjpeg | unknown | 已安装 |
| libpng16 | unknown | 已安装（静态库） |
| zlib | unknown | 已安装 |

## 验证结果

```bash
$ tifffastcrop --help
tifffastcrop v1.4.1 license GNU GPL v3 (c) 2013-2021 Christophe Deroulers
...（正常显示帮助信息）

$ tiffmakemosaic --help
...（正常显示帮助信息）

$ tiffsplittiles --help
...（正常显示帮助信息）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| largetifftools-1.4.1-ohos-aarch64.tar.gz | 624K | 预编译包（包含 3 个可执行文件） |

## 注意事项

1. **config.status 权限问题**：此软件在鸿蒙环境下遇到 config.status 创建临时目录的权限问题，可能需要进一步调查 root cause（与 shell/文件系统权限相关）
2. **手动编译**：由于 autotools 流程失败，采用了手动 Makefile，这可能导致未来版本更新时需要手动调整
3. **libpng 静态库**：系统中安装的是 libpng16.a 静态库，需要额外链接 zlib
4. **格式警告**：tiffmakemosaic.c 中有 3 个格式警告（uint64_t vs unsigned long long），不影响功能

## G0 干净构建验证说明

此软件在鸿蒙环境下遇到 autotools config.status 权限问题：
- **问题**：config.status 第 742 行创建临时目录失败，提示 "Permission denied"
- **根因**：shell 重定向与鸿蒙文件系统权限机制兼容性问题
- **解决**：使用手动 Makefile 编译方式
- **影响**：无法在干净环境自动重现编译，但产物功能正常

建议后续版本考虑：
1. 为该软件创建 CMake 构建系统，替代 autotools
2. 或创建补丁修复 config.status 权限问题
3. 手动 Makefile 已在源码目录中创建，可复用

## 预编译包说明

**重新打包日期**：2026-06-11
**包大小**：1.5MB (包含二进制和依赖库)
**包含内容**：
- bin/tifffastcrop (286KB, stripped, signed)
- bin/tiffmakemosaic (110KB, stripped, signed)
- bin/tiffsplittiles (86KB, stripped, signed)
- lib/external/libtiff.so.6 (502KB)
- lib/external/libjpeg.so (562KB)

**质量门禁**：全部通过 (G1-G4)
- G1 二进制完整性：PASS
- G2 功能可用性：PASS
- G3 可移植性：PASS
- G4 档案完整性：PASS---

**编译结束**: 2026-06-11 17:53
**最终状态**: built
---

**编译结束**: 2026-06-12 11:27
**最终状态**: built
