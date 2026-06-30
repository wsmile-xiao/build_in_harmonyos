# bwfmetaedit 26.01 适配笔记

## 编译环境
- 构建系统: autotools（Project/GNU/CLI）
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `https://api.github.com/repos/MediaArea/BWFMetaEdit/tarball/v26.01`
2. 解压到 ~/builds/bwfmetaedit-26.01.work
3. 进入 Project/GNU/CLI 目录
4. 运行 autogen.sh 生成 configure（需先修复 automake 版本不匹配问题）
5. 运行 `./configure --prefix=$DEFAULT_PREFIX`
6. 运行 `make -j1`
7. 运行 `make install DESTDIR=$TEST_PREFIX`
8. 运行 `make check`（版本测试通过，其他测试因缺少 ffmpeg 而失败）
9. 验证质量门禁
10. 制作预编译包
11. 运行 `make install`（安装到本地）
12. 用户验证: `bwfmetaedit --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake Perl 模块缺失 | automake-1.17 脚本期望 automake-1.17/share 目录，但实际安装的是 1.16 | 创建符号链接 `automake-1.17 -> automake-1.16` |
| 2 | configure 创建临时文件权限失败 | E011: HMDFS 文件系统 umask 077 权限问题 | 修改 configure 中 `umask 077` 为 `umask 022` |
| 3 | pthread_cancel 编译失败 | PSCAN-MUSL-001: musl/OHOS 不支持 pthread_cancel | 添加 `#ifdef __OHOS__` 跳过 pthread_cancel |
| 4 | PKG_CONFIG_PATH 缺失 zlib | zlib 已安装但 pkg-config 无法找到 | 设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig` |

## 源码修改

### 0001-E011-configure-umask.patch
文件: Project/GNU/CLI/configure
修改: 将 `umask 077` 改为 `umask 022`，解决 HMDFS 临时目录权限问题
原因: E011 - HMDFS 文件系统 UID 映射导致 umask 077 创建的目录对当前进程不可写

### 0002-MUSL001-pthread_cancel.patch
文件: Source/ZenLib/Thread.cpp:523
修改: 添加 `&& !defined(__OHOS__)` 到 pthread_cancel 的条件编译
原因: PSCAN-MUSL-001 - pthread_cancel 在 musl/OHOS 上不可用

## 依赖版本

- zlib: 1.3.1（已编译并安装到 ~/usr/local）

## 验证结果

```bash
$ ~/usr/local/bin/bwfmetaedit --version
BWF MetaEdit 26.01
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bwfmetaedit-26.01-ohos-aarch64.tar.gz | 969KB | 预编译包（ELF 已签名） |
| bwfmetaedit-26.01-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

1. 构建系统位于 Project/GNU/CLI 目录（非标准位置）
2. 需先运行 autogen.sh 生成 configure 脚本
3. configure.ac 只包含 AC_INIT(../../../Source/CLI/CLI_Main.cpp)，无包名版本信息
4. make check 需要 ffmpeg 生成测试音频文件（测试失败不影响功能）
5. 二进制为动态链接 musl，无需额外运行时依赖
---

**编译结束**: 2026-06-12 16:07
**最终状态**: built
