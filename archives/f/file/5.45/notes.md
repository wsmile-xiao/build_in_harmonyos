# file 5.45 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-03-23
- 编译器: clang (Clang 15.0.4, LLVM)
- 状态: partial（test-report 缺失导致降级，但 72/72 测试全通过）

## 编译步骤
1. 下载源码 `https://astron.com/pub/file/file-5.45.tar.gz` 并解压
2. 修补 config.sub 添加 `linux-ohos*` kernel-os 白名单
3. 修补 man page 和源文件中的硬编码路径
4. 配置: `./configure --prefix=$HOME/usr/local --disable-libseccomp --enable-static --disable-shared LDFLAGS=-static`
5. `make`
6. `make install` 到 staging 目录
7. 测试: 72/72 全通过
8. 制作预编译包 (8.9MB)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 OHOS | 缺少 `linux-ohos*` 白名单 | 修补 config.sub |
| 2 | 动态链接 .so 软链接无法加载 | 鸿蒙 SELinux 限制 | 使用静态链接 `--enable-static --disable-shared LDFLAGS=-static` |
| 3 | man page 路径错误 | 硬编码路径 | 修补 doc-file.1, doc-libmagic.3, doc-magic.4 |
| 4 | 源码路径问题 | 硬编码路径 | 修补 src-file, src-magic.h, tests-test |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.sub | 添加 linux-ohos* 白名单 | ✅ 0001-config.sub.patch |
| doc/file.1 | 修正路径 | ✅ 0002-doc-file.1.patch |
| doc/libmagic.3 | 修正路径 | ✅ 0003-doc-libmagic.3.patch |
| doc/magic.4 | 修正路径 | ✅ 0004-doc-magic.4.patch |
| src/file | 修正路径 | ✅ 0005-src-file.patch |
| src/magic.h | 修正路径 | ✅ 0006-src-magic.h.patch |
| tests/test | 修正路径 | ✅ 0007-tests-test.patch |

## 依赖版本
- zlib, bzip2, xz/lzma

## 验证结果
- file --version → file-5.45 ✅
- 测试: 72/72 全部通过 ✅
- 功能验证: ELF/zlib/bzip2/xz 格式识别正常 ✅
- 质量门禁: PASS

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| file-5.45-ohos-aarch64.tar.gz | 8.7MB | 主包（静态链接） |

## 注意事项
- 必须使用静态链接，动态链接因 SELinux 限制不可用
- file 命令依赖 magic.mgc 数据文件，确保安装路径正确
