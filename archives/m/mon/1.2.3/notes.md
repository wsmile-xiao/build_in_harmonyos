# mon 1.2.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure/autotools）
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony (aarch64, musl libc)
- 状态: published

## 编译步骤

1. 下载源码包（GitHub 直连超时，使用 gh-proxy.com 镜像下载）
2. `ohc-run.py init-build mon 1.2.3 --url=... --force` 初始化编译环境
3. `cd $BUILD_SRC_DIR` 进入源码目录
4. `make CFLAGS="-D_GNU_SOURCE -std=c99 -I deps/ -fPIC -O2" CC=clang -j1` 编译
5. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` Staging 安装（R20 DESTDIR 模式）
6. `make install PREFIX=$DEFAULT_PREFIX` 本地安装验证
7. `ohc-run.py package mon 1.2.3` 打包预编译包
8. `ohc-run.py finish mon 1.2.3 published` 收尾归档

注意：mon 无 configure 脚本，直接使用 make 编译。为通过 clean-verify G0，
创建了 configure wrapper 脚本（见补丁 0002-configure.patch）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 (Errno 110) | 平台网络限制，GitHub 直连不可达 | 使用 gh-proxy.com 镜像下载 tarball |
| 2 | clean-verify G0 失败: configure not found | mon 是纯 Makefile 项目，无 configure 脚本；clean_verify.py 默认运行 `bash ./configure` | 创建最小 configure wrapper 脚本，接受 --prefix 并写入 config.mk |
| 3 | Makefile install 不支持 DESTDIR (R20 违规) | 原始 install 目标仅 `cp -f mon $(PREFIX)/bin/mon`，无 DESTDIR 和 mkdir | 补丁修改为 `mkdir -p $(DESTDIR)$(PREFIX)/bin` + `cp -f mon $(DESTDIR)$(PREFIX)/bin/mon` |
| 4 | Makefile 不读取 configure 设置的 PREFIX | Makefile 用 `PREFIX ?=` 但不 include config.mk | 添加 `-include config.mk` 到 Makefile |
| 5 | verify-build G4 失败: manifest 缺少 build_system | manifest 模板用 `system:` 但 verify_build.py 查找 `build_system:` | 添加 `build_system: makefile` 到 manifest |
| 6 | verify-build G2 警告: 无二进制文件 | DESTDIR 模式安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`，但 G2 查找 `$TEST_PREFIX/bin/` | 补充 flat staging 安装 `make install PREFIX=$TEST_PREFIX` |
| 7 | 软件级 README.md 缺失 | finalize-archive Phase 2 检查软件级文件 | 创建 archives/m/mon/README.md |
| 8 | 软件级 manifest.yaml 缺失 | 归档规范要求软件级 manifest | 创建 archives/m/mon/manifest.yaml |

## 源码修改

### 补丁 0001-Makefile.patch
- 文件: Makefile
- 修改内容:
  - install 目标添加 `mkdir -p $(DESTDIR)$(PREFIX)/bin` 确保目录存在
  - install 目标 cp 命令改为 `cp -f mon $(DESTDIR)$(PREFIX)/bin/mon` 支持 DESTDIR
  - 添加 `-include config.mk` 使 configure wrapper 可设置 PREFIX
- 原因: R20 要求 DESTDIR 模式，原始 Makefile 不支持

### 补丁 0002-configure.patch
- 文件: configure（新增）
- 修改内容: 创建最小 configure wrapper 脚本
  - 接受 `--prefix=PATH` 参数
  - 写入 `PREFIX = PATH` 到 config.mk
  - 退出码 0
- 原因: clean_verify.py 默认运行 `bash ./configure`，纯 Makefile 项目需要此 wrapper 通过 G0

## 依赖版本

无外部依赖。mon 是纯 C 语言项目，仅依赖标准库（stdio, stdlib, unistd, signal 等）。

## 验证结果

```bash
$ mon --version
1.2.3

$ mon --help
  Usage: mon [options] <command>
  Options:
    -V, --version                 output program version
    -h, --help                    output help information
    -l, --log <path>              specify logfile [mon.log]
    ...

$ python3 ohc-run.py clean-verify mon 1.2.3
✅ G0 干净构建验证通过

$ python3 ohc-run.py verify-build mon 1.2.3
✅ 质量报告: PASS (G1-G4 全通过)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/mon-1.2.3-ohos-aarch64.tar.gz | 82,977 bytes (81KB) | 预编译包（ELF 签名） |
| packaging/mon-1.2.3-ohos-aarch64-debug.tar.gz | 31,255 bytes (31KB) | 调试符号包 |
| patches/0001-Makefile.patch | 545 bytes | DESTDIR 支持 + config.mk include |
| patches/0002-configure.patch | 550 bytes | configure wrapper 脚本 |
| reports/test-report.md | — | 测试报告（含真实执行输出） |
| reports/quality-report.md | — | G0-G4 质量门禁报告 |

## 注意事项

- mon 是纯 Makefile 项目，无 configure 脚本和测试套件
- GitHub 直连在本平台不可达，需使用镜像下载
- clean_verify.py 默认使用 autotools 流程，对 Makefile-only 项目需创建 configure wrapper
- verify_build.py 的 G2 检查找 `$TEST_PREFIX/bin/`，需额外做 flat staging 安装
- G3 的 RPATH/签名警告对简单命令行工具不阻塞（mon 无外部库依赖）

---

**编译结束**: 2026-06-25 15:49
**最终状态**: published
