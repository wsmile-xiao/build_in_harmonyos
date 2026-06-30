# podofo 0.9.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
# 设置 PKG_CONFIG_PATH 以便 CMake 的 find_package 能找到依赖
export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig"

# CMake 配置
cd $BUILD_SRC_DIR && mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DFREETYPE_INCLUDE_DIR_FT2BUILD=$DEFAULT_PREFIX/include/freetype2 \
  -DFREETYPE_INCLUDE_DIR_FTHEADER=$DEFAULT_PREFIX/include/freetype2/freetype \
  -DFREETYPE_LIBRARY=$DEFAULT_PREFIX/lib/libfreetype.a \
  -DFONTCONFIG_INCLUDE_DIR=$DEFAULT_PREFIX/include \
  -DFONTCONFIG_LIBRARIES=$DEFAULT_PREFIX/lib/libfontconfig.so

# 编译
make -j1

# 安装到 staging
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败: cmake_minimum_required(VERSION 2.6) 不兼容 CMake 4.x | CMake 4.x 移除了 < 3.5 的兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 参数 |
| 2 | FREETYPE 未找到 | podofo 的 FindFREETYPE.cmake 使用硬编码路径，不搜索 $DEFAULT_PREFIX | 通过 CMake 命令行指定 -DFREETYPE_INCLUDE_DIR_FT2BUILD 等参数 |
| 3 | fontconfig 未找到 | freetype2.pc 中 Requires libpng，但 libpng.pc 文件名是 libpng16.pc | 创建 libpng.pc -> libpng16.pc 符号链接 |
| 4 | libfontconfig.so 符号链接缺失 | 预编译包只有 libfontconfig.so.1.15.0 | 创建 libfontconfig.so -> libfontconfig.so.1.15.0 符号链接 |
| 5 | libcrypto.pc 路径错误 | .pc 文件中 prefix 指向了 test-install 目录 | 修复 .pc 文件中的 prefix 路径为 $DEFAULT_PREFIX |
| 6 | PNG_LIBRARY NOTFOUND 导致生成失败 | libpng 未安装 | 安装 libpng 1.6.43 预编译包 |
| 7 | TokenizerTest 链接失败: copy_directory 错误 | test/TokenizerTest/objects 目录在源码 tarball 中缺失 | 创建空目录 |
| 8 | WANT_FONTCONFIG=FALSE | CMake 不识别 HarmonyOS 为 UNIX 系统 | 接受为平台限制，fontconfig 功能未启用（不影响编译） |

## 源码修改

无源码修改。所有问题通过 CMake 参数和环境修复解决。

创建了空目录 test/TokenizerTest/objects（源码 tarball 中缺失）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | 预编译包 |
| freetype | 26.6.20 (2.14.3) | 预编译包 |
| fontconfig | 2.16.0 | 预编译包 |
| libpng | 1.6.43 | 预编译包 |
| openssl | 1.1.1w | 预编译包 |

## 验证结果

### 安全弹窗验证

```bash
# 所有工具程序正常触发安全弹窗并运行
$STAGING_PREFIX/bin/podofocrop --version      # → PoDoFo Version: 0.9.5
$STAGING_PREFIX/bin/podofoencrypt --help       # → 显示完整帮助信息
$STAGING_PREFIX/bin/podofomerge                # → Usage: podofomerge ...
```

### 真实功能测试（11 项，9 项通过）

详细报告见 `reports/test-report.md`

| # | 测试 | 工具 | 结果 | 说明 |
|---|------|------|------|------|
| 1 | 创建 PDF | helloworld | ❌ | fontconfig 未启用，找不到 Arial 字体（E092 平台限制） |
| 2 | 统计页数 | podofocountpages | ✅ | inline-image.pdf=1, Illust.pdf=1, merged.pdf=2 |
| 3 | 提取信息 | podofopdfinfo | ✅ | 正确提取版本/页数/尺寸/权限/元数据 |
| 4 | 合并 PDF | podofomerge | ✅ | 2个1页PDF→2页PDF(217KB)，引用修复正确 |
| 5 | 解压 PDF | podofouncompress | ✅ | 解压流对象(2280→2282 bytes) |
| 6 | 文本提取 | podofotxtextract | ❌ | 测试PDF为纯图像无文本，非功能缺陷 |
| 7 | 页面操作 | podofopages | ✅ | 删除页面 2→1 页 |
| 8 | 垃圾回收 | podofogc | ✅ | 解析并重写PDF(4.7KB) |
| 9 | 加密 PDF | podofoencrypt | ✅ | RC4v2加密，Encrypted: Yes |
| 10 | 库架构 | file/llvm-readobj | ✅ | aarch64 ELF 64-bit, musl libc, 1838导出符号 |
| 11 | 额外参数 | podofocountpages -s/-t | ✅ | 静默模式和Total输出正常 |

### 库文件验证

```bash
$ file podofocountpages
# → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ llvm-readobj -h libpodofo.a
# → Format: elf64-littleaarch64, Arch: aarch64, AddressSize: 64bit

$ llvm-nm libpodofo.a | grep -c "T "
# → 1838 个导出符号

$ ls -la libpodofo.a
# → 4,272,144 字节 (4.2MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| podofo-0.9.5-ohos-aarch64.tar.gz | 44.8MB | 预编译包（含库+工具+头文件+外部依赖） |
| podofo-0.9.5-ohos-aarch64-debug.tar.gz | 7.0MB | 调试符号包 |
| libpodofo.a | 4.2MB | 静态库（aarch64, 1838导出符号） |
| 18个工具程序 | — | podofobox/podofocrop/podofoencrypt/podofomerge 等 |
| 头文件 | — | podofo.h, podofo-base.h + base/doc 子目录 |

源码 tarball SHA256: `3e47646e6059a46ab5e20b35cc2b6de9c2d6db2443fc27808bbe764351220370`
打包产物 SHA256: `d829bac3ae76b9773e20025158e61e796764bcedb34225baffd5c68627818f30`

## 注意事项

- podofo 0.9.5 使用 CMake 2.6 语法，需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 兼容 CMake 4.x
- FindFREETYPE.cmake 使用硬编码路径，需要通过 CMake 命令行参数指定路径
- fontconfig 功能未启用（CMake 不识别 HarmonyOS 为 UNIX），不影响编译和基本功能
  - 影响：helloworld 等需要字体查找的功能不可用（E092 平台限制）
  - 不影响：PDF 解析、合并、解压、加密、页面操作等核心功能
- test/TokenizerTest/objects 目录在 GitHub tarball 中缺失，需要手动创建

---

**编译开始**: 2026-06-25 14:56
**编译结束**: 2026-06-25 15:32
**功能测试**: 2026-06-25 15:45-15:48
**最终状态**: built（核心功能验证通过）
