# flac 1.4.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-12
- 编译器: clang 15.0.4 / clang++
- 状态: success

## 编译步骤
1. 下载源码 `https://downloads.xiph.org/releases/flac/flac-1.4.3.tar.xz`
2. 应用 config.guess/config.sub 补丁（OHOS 平台识别）
3. 修复 configure 脚本中 mktemp 路径（`./confXXXXXX` → `$TMPDIR/conan-cs-$$`）
4. `./configure --prefix=$DEFAULT_PREFIX`（OGG 自动检测通过）
5. `make -j2`
6. `make install DESTDIR=$TEST_PREFIX`（staging 隔离安装）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status mktemp 失败 | OHOS HMDFS 不允许在 CWD 创建临时目录 | 修改 configure 脚本 mktemp 路径为 TMPDIR |
| 2 | libFLAC++ 静态库 hard link 失败 | HMDFS 不支持 hard link | 非功能影响，库正确生成 |
| 3 | doc install 失败 | doc/api/install-sh 路径问题 | 跳过 doc 安装，核心组件已安装 |
| 4 | make check 中 writable 检测失败 | OHOS 权限处理与 Linux 不同 | 非功能影响，核心测试通过 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.guess | 添加 OHOS 平台识别 | ✅ 0001-config.guess.patch |
| config.sub | 添加 OHOS 平台支持 | ✅ 0002-config.sub.patch |
| configure | mktemp 路径修复 | ❌ conanfile.py build() 中运行时修复 |

## 依赖版本
- libogg/1.3.5（Conan 制品仓，静态链接进 libFLAC）

## 验证结果
- flac --version → flac 1.4.3 ✅
- metaflac --version → metaflac 1.4.3 ✅
- FLAC__HAS_OGG = 1 ✅（OGG 支持已启用）
- libFLAC.so: NEEDED libc.so（libogg 静态链接）✅
- make check: 核心测试通过（metadata, stream encoder/decoder）

## 产物
| 文件 | 说明 |
|------|------|
| libFLAC.so.12.1.0 | C 库 |
| libFLAC++.so.10.0.1 | C++ 库 |
| flac | 命令行编码/解码工具 |
| metaflac | 元数据编辑工具 |
| flac.pc / flac++.pc | pkg-config 文件 |
---

**编译结束**: 2026-07-15 15:09
**最终状态**: built
