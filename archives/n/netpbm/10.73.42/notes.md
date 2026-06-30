# netpbm 10.73.42 适配笔记

## 编译环境
- 构建系统: custom-perl (交互式 Perl 配置脚本)
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 netpbm 使用特殊的交互式 Perl 配置脚本 (configure.pl)，不支持标准 autotools 参数如 `--prefix`，因此采用手动创建 config.mk 文件的方式：

```bash
# 1. 手动创建 config.mk 文件（关键配置）
# 配置内容见下文

# 2. 编译
cd /storage/Users/currentUser/tmpexport/builds/netpbm-10.73.42.work
make -j1

# 3. 安装到 staging 目录
make package pkgdir=/storage/Users/currentUser/tmpexport/test-install-netpbm-10.73.42

# 4. 使用 ohc-run.py 制作规范的预编译包
python3 scripts/ohc-run.py package netpbm 10.73.42
```

## config.mk 关键配置

```makefile
# 编译器设置
CC = clang
LD = $(CC)
LINKERISCOMPILER = Y

# 静态库（避免 RPATH 问题）
NETPBMLIBTYPE = unixstatic
NETPBMLIBSUFFIX = a

# 禁用可选依赖（简化编译）
TIFFLIB = NONE
JPEGLIB = NONE
PNGLIB = NONE
ZLIB = NONE
X11LIB = NONE

# 禁用网络功能（平台限制）
OMIT_NETWORK = Y
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure.pl 不接受 --prefix | netpbm 使用交互式 Perl 配置脚本，非标准 autotools | 手动创建 config.mk 文件 |
| 2 | 编译时缺少 PNG/JPEG/TIFF/X11 库 | 这些是可选依赖 | 设置为 NONE 禁用相关工具 |
| 3 | 网络功能受限 | HarmonyOS 平台网络 API 限制 | OMIT_NETWORK=Y |

## 源码修改

无需修改源码，仅手动创建 config.mk 配置文件。

## 依赖版本

无外部依赖（禁用了所有可选库）。

## 验证结果

```bash
# 二进制验证
/storage/Users/currentUser/usr/local/bin/pbmtext --version
# 输出: netpbm 10.73.42

# 制品文件
ls archives/n/netpbm/10.73.42/packaging/
netpbm-10.73.42-ohos-aarch64.tar.gz      (~45MB)
netpbm-10.73.42-ohos-aarch64-debug.tar.gz (~12MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| netpbm-10.73.42-ohos-aarch64.tar.gz | ~45MB | 标准预编译包 |
| netpbm-10.73.42-ohos-aarch64-debug.tar.gz | ~12MB | 调试版预编译包 |

## 注意事项

1. **构建系统特殊**: netpbm 使用交互式 Perl 配置脚本，需要手动处理配置
2. **可选依赖**: 如需 PNG/JPEG/TIFF/X11 支持的工具，需要先编译对应依赖库
3. **静态库**: 使用静态库避免 RPATH 问题
4. **制品位置**: 预编译包位于 archives/n/netpbm/10.73.42/packaging/ 目录

---

**编译结束**: 2026-05-22 16:15
**最终状态**: built (编译成功，制品已生成)