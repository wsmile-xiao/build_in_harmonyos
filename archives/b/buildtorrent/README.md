# buildtorrent — 软件包说明

## 概述

buildtorrent 是 Claude Heiland-Allen 开发的 .torrent 文件生成命令行工具（2007-2024）。
给定输入文件或目录，生成可供 BT 客户端使用的 .torrent 文件，支持 announce/announce-list、
DHT 节点（BEP-5）、WebSeed（BEP-19）、私有标志（BEP-27）、MD5 附加、目录排序、创建日期/
创建者覆盖与 magnet 链接输出。本包适配上游 0.9.1 正式源码包（2024-08-21 发布）。

- 产物：`bin/buildtorrent`（上游唯一 bin_PROGRAMS）+ `share/man/man1/buildtorrent.1`
- 源码：`buildtorrent.c` + 自带 `md5.c/md5.h`、`sha1.c/sha1.h`，无第三方依赖
- 许可：GPL-2.0-or-later（COPYING 为 GNU GPL v2）

## OHOS 适配要点（0.9.1）

| 问题 | 处理 |
| --- | --- |
| 自带 config.guess/config.sub 为 2022 年版，早于 HarmonyOS | OHOS 下传 portable GNU `--build/--host=aarch64-unknown-linux-gnu` 过 configure 平台识别；编译器仍为 OHOS clang |
| HMDFS 拷贝会剥离 configure 可执行位 | build() 内先 `chmod +x configure` 再 configure |
| 上游无测试套件 | 不调用 `make check`；功能覆盖由 test_package/test_buildtorrent.sh 提供（5 项内容级验证） |
| `versionsort` 为 GNU 扩展 | 上游已用 `#ifdef _GNU_SOURCE` 守卫并回退到 `alphasort`，无需补丁 |

## 构建

- 构建系统：Autoconf 2.71 + automake 1.16.5（随包发布 configure/Makefile.in）
- Conan 配方：`archives/b/buildtorrent/0.9.1/conanfile.py`（AutotoolsToolchain，`-j1`）
- 上游测试：无（Makefile.am 仅 bin_PROGRAMS/man_MANS，无 TESTS/check_PROGRAMS）
- 设备验证：OHOS 6.0 / aarch64 / clang 15，`conan create` + test_package 通过

## 安装产物

- `bin/buildtorrent` — torrent 生成主程序
- `share/man/man1/buildtorrent.1` — 手册页
- `licenses/COPYING` — 许可证文本

## 测试统计口径

- 上游：0 个测试程序（经审计确认无测试套件，MANIFEST.yml 含 upstream_test_audit）
- test_package：1 个 shell 功能脚本，5 项断言（--version/--help/单文件生成/确定性复现/magnet）

## 上游

- 源：`https://mathr.co.uk/web/buildtorrent/buildtorrent-0.9.1.tar.gz`
- 项目主页：https://mathr.co.uk/web/buildtorrent.html
- 代码仓库：https://code.mathr.co.uk/buildtorrent.git
