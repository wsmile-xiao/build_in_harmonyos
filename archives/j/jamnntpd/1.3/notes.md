# jamnntpd 1.3 适配笔记

## 编译环境
- 构建系统: makefile（上游为手写 Makefile + Makefile.linux 分发器，jamlib 子 make 产 jamlib.a，无 configure、无 make check）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS 包装脚本，默认 target aarch64-linux-ohos + sysroot + 链接期 --code-sign）
- 状态: built

## 源码获取（E347 预置缓存）
- 官方发布物只有 zip：`https://downloads.sourceforge.net/project/jamnntpd.ftnapps.p/1.3/jamnntpd-1.3.zip`（122265 B，sha256 `132f9936…876a44`，顶层目录 `jamnntpd-1.3/`，strip_root=True）。
- SourceForge 下载端点对数据中心 IP 一律 403 反爬（设备/脚本直取均实测失败；浏览器住宅网络取回多次字节一致）。设备侧按 E347 把已验证官方 zip 预置到共享 `core.sources:download_cache`（`~/tmp/ch/dlcache/s/<sha256>`）后 `conan create` 命中缓存；conandata.yml 保留官方 URL，镜像/pool URL 不进活文件。
- Ubuntu pool 的 `jamnntpd_1.3.orig.tar.gz`（sha256 454f61c0…）是 Debian 对同一内容的 repack（容器格式不同，哈希必然不等），仅作同源旁证，不作 URL 来源。

## 编译步骤
```sh
# jamlib 静态库
make -C src/jamlib -f Makefile.linux \
  CC="clang -D__LINUX__ -Ulinux -include fcntl.h -Wall" AR="llvm-ar rcu"
llvm-ranlib src/jamlib/jamlib.a
# 主程序（jamnntpd + makechs）
make -C src -f Makefile.linux CC="clang -Ulinux -Wall" STRIP=":"
```
`STRIP=":"` 是刻意的：OHOS clang 包装在链接期给 ELF 做 code-sign，事后 strip 会破坏签名导致无法加载；产物不剥离符号交付。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | jamlib/主程序全部 `unknown type name 'ulong'/'ushort'` | `jam.h` 用 `#ifndef linux` 跳过自带 typedef（假设 glibc 经 sys/types.h 暴露 ulong）；OHOS musl 即使 `_GNU_SOURCE` 也不给 uchar/ulong 走默认包含链 | 编译加 `-Ulinux`，让 jam.h 自带 typedef 生效（纯 flag，无源码补丁） |
| 2 | `mbase.c` `struct flock` 不完整、`F_WRLCK` 未定义 | 上游只 include `<sys/file.h>`；glibc 的 sys/file.h 会拉 fcntl.h，OHOS 精简版 sys/file.h 不含 fcntl.h | 编译加 `-include fcntl.h`（flag-only） |
| 3 | 产物链接后运行期加载风险 | 链接后 strip 破坏 code-sign 段 | `STRIP=":"` 跳过 strip |
| 4 | SF 官方 URL 脚本/设备 403 | SourceForge 反爬（数据中心 IP 段） | E347 预置 conan content-addressed 下载缓存；URL/sha256 均取官方 zip 本体 |

## 上游测试账本（§10.1）
- `N_static = 0`：上游无 configure/ctest/add_test/任何测试注册入口（72 文件核对）。
- 执行证据：配方 `build()` 内真实执行 `make -f Makefile.linux check`，构建日志逐字留下 make 报错（`No rule to make target 'check'`，见本目录 reports/ 与 conan 构建日志），按"上游无自动化测试"收口。
- `N_registered = 0`，`N_executed = 0`（上游侧），未执行分类 = 0（不存在可执行项）。
- `N_consumer = 2`（test_package：①loopback NNTP 协议守护进程消费者测试，断言 200 greeting/500/411/340/205 五类应答码；②makechs 真实生成 .chs 表并断言表头/字符集名/0x41→0x62 映射行）。
- 适配后合计 = 0（上游）+ 2（消费者）= 2。

## 消费者测试设计（B 草稿机制载体）
无 root、无 GUI 的 OHOS 上对 TCP 协议守护进程做真实消费者测试的完整手法：
1. 配置面全部经 argv 重定向到可写目录（`-allow/-groups/-xlat/-logfile`，上游默认 `/etc/`、`/var/spool/log/` 不可写）；
2. 端口可得性：用 `bind(("127.0.0.1", 0))` 取空闲高端口再交给 `-port`（不假设 119/5000 可绑）；
3. groups 配置必须 ≥1 条（空则 readgroups 失败断开）、xlat 必须含 post 条目（缺则 readxlat 失败断开）、.chs 引用包内 `res/xlat/`；
4. 自写 NNTP 客户端逐连接断言协议状态机应答码（greeting 200、未知命令 500、缺组 411、POST 340 系列、QUIT 205），全部单行应答避免多行终结歧义；
5. 附属生成工具 makechs 实跑并断言生成物内容；
6. 服务进程 terminate/kill 兜底 + 15s 就绪等待。

## 验证结果
设备实测（2026-09-24，hw-6）：
- 手工交叉编译 RC=0，`file` 确认 ELF 64-bit aarch64 musl 动态链接；
- `./jamnntpd -h` 可执行并打印 usage（签名有效）；
- loopback 起服务 + Python NNTP 客户端：greeting `200 Welcome to JamNNTPd/Linux 1.3`，服务端日志 `Connection established/closed` 正常。
- conan create 全链路验证见 reports/ 与后续 CI。
---

**编译结束**: 2026-09-24 16:36
**最终状态**: built
