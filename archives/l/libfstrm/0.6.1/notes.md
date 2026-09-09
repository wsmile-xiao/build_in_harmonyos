# libfstrm 0.6.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
# 上游源码：farsightsec/fstrm v0.6.1（libfstrm 为 fstrm 库的 Debian/包名）
# 源码 tarball：gh-proxy 镜像下载（github.com 直连超时），
#   sha256=4f0f7ad2b760119c441aba58271e84de683b3cc138530d02710896641866e2d2
# 构建工具准备（cmd-pkgs 预编译包）：
#   automake 1.16.5、libtool 2.4.7、autoconf 2.72（已有）、libevent 2.1.12
# 工具链路径修复（本机环境，不进 PR）：
#   perl -> /data/service/hnp/bin/perl
#   bash -> $(which bash)、sed -> $(which sed)、autoconf -> $(which autoconf)

cd $BUILD_SRC_DIR
export PERL5LIB=/storage/Users/currentUser/usr/local/share/automake-1.16
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

autoreconf -fvi                       # 源码不含 configure，需生成
# 知识 E011：HMDFS umask 077 导致 config.status 临时目录不可写，
#   sed -i 's/umask 077/umask 022/g' configure 后重跑
./configure --prefix=$DEFAULT_PREFIX
make -j2
make check                            # 7/9 PASS，2 FAIL 见下
make install DESTDIR=$TEST_PREFIX     # staging 隔离验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连下载超时 (Errno 110) | 网络不可达 github.com | gh-proxy.com 镜像下载 v0.6.1 tarball，核验 tag commit 1d6e11d750df |
| 2 | autoreconf: aclocal/libtoolize/automake not found | 环境缺 automake/libtool，perl 路径不一致 | cmd-pkgs 安装 automake 1.16.5 + libtool 2.4.7；PERL5LIB 指向 automake-1.16 perl 模块；补齐 usr/local/bin 下的 perl/bash/sed/autoconf 软链（本机工具链，不进 PR） |
| 3 | configure: config.status 报 `can't create ./confXXX/subs1.awk: Permission denied` | HMDFS umask 077 临时目录权限（知识 E011） | `sed -i 's/umask 077/umask 022/g' configure` 后重跑 configure，通过 |
| 4 | configure: No package 'libevent' found | configure 默认构建 fstrm_capture 等程序需 libevent>=2 | cmd-pkgs 安装 libevent 2.1.12，PKG_CONFIG_PATH 指向其 .pc 后通过 |
| 5 | make check: FAIL t/run_test_fstrm_io_unix.sh（bind: Operation not permitted，Signal 6） | OHOS SELinux 限制 Unix domain socket bind（知识 E024，平台限制） | 属平台限制非库缺陷；TCP 通道等价用例 PASS；AF_UNIX 用例记录平台限制 |
| 6 | make check: FAIL t/program_tests/test_fstrm_replay.sh（unix socket 段失败） | 同上：fstrm_capture 无法 bind AF_UNIX 导致 event loop 创建失败 | 同 E024 平台限制；该脚本 TCP socket 段 PASS（wrote 12 frames, 242 bytes） |

## 源码修改

无（本次未修改源码，无补丁；autotools 生成的 configure 等为本地构建产物，不进归档）。

## 依赖版本

- libevent 2.1.12（仅 configure/fstrm_capture 参考程序构建需要；制品仓 ohpcd 已有 libevent/2.1.12、2.1.13 配方）
- pkg-config 0.29.2

## 验证结果

```bash
# 上游测试（make check）: TOTAL 9 = PASS 7 + FAIL 2
#   FAIL 均为 OHOS SELinux 限制 AF_UNIX bind（E024 平台限制，TCP 等价用例 PASS）：
#     t/run_test_fstrm_io_unix.sh          bind: Operation not permitted
#     t/program_tests/test_fstrm_replay.sh unix socket 段失败，tcp socket 段 PASS
# 实测复现：AF_UNIX bind -> PermissionError EPERM；AF_INET bind 127.0.0.1 -> OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools） |
| conandata.yml | 源码 v0.6.1 官方 URL + sha256 |
| test_package/ | Conan L1 测试包 |

## 注意事项

- 上游仓库为 `farsightsec/fstrm`（分析端任务头 source_url 写作 libfstrm 的包名形式，实际 GitHub 仓库名为 fstrm）；v0.6.1 tag commit = 1d6e11d750dfa8d15419814dfe0aa86d80000741。
- fstrm_capture/replay/dump 为参考程序，库本体 libfstrm 无需 libevent；conan 配方默认开启 programs 也可，但依赖注入仅限私有 prefix。
---

**编译结束**: 2026-09-07 01:31
**最终状态**: published
