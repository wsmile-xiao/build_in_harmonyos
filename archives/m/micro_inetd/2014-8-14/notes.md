# micro_inetd 2014-8-14 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，单 C 文件，无 configure）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标）
- 状态: built

## 上游核验

| 项目 | 结果 |
|------|------|
| 官方发布源 | https://www.acme.com/software/micro_inetd/（Jef Poskanzer, ACME Labs） |
| 版本日期 | 2014-08-14（tarball 内文件 mtime 与站点 Last-Modified 一致：2014-08-14） |
| 源码 URL | https://www.acme.com/software/micro_inetd/micro_inetd_14Aug2014.tar.gz |
| SHA256 | `15f5558753bb50ed18e4a1445b3e8a185f3b1840ec8e017a5e6fc7690616ec52`（与 FreeBSD ports distfiles、Homebrew formula 三方一致） |
| License | BSD-2-Clause（源码头 1996,2000 Jef Poskanzer，两条款 + 免责声明） |
| 构建方式 | `make`（上游 Makefile：CC=cc，LDFLAGS=-s，install 硬编码 /usr/local） |
| 依赖 | 无第三方依赖，仅系统 libc（musl）；readelf -d 仅 NEEDED libc.so |

> acme.com 原站当前仍可达（HTTP 200, mini_httpd），且哈希与 FreeBSD ports-distfiles
> 镜像完全一致，故 conandata.yml 采用原站 URL（R39 官方源优先）。

## 上游测试审计（确定数量）

上游 **0 个测试**：
- `make -n check` → `No rule to make target 'check'`（Makefile 只有 all/install/clean 目标）
- 无 tests/、test/ 目录，无任何 `*test*.c` / `example*.c` 文件
- 发布物仅 README、Makefile、micro_inetd.c、micro_inetd.1 四个文件
- Homebrew formula 的 test 也是消费者侧 socket 行为测试（自写，非上游）

因此可运行的上游测试数量为 **0**，全部验证由 test_package 承担（L1c 口径：
MANIFEST.yml 声明 upstream_tests: []，原因"上游无测试套件"）。

## 编译步骤

```bash
# 探索阶段（$HOME/tmp/mi-build）
clang -O -fPIE -pie -D_FORTIFY_SOURCE=2 -ansi -pedantic -U__STRICT_ANSI__ \
  -Wall -Wpointer-arith -Wshadow -Wcast-qual -Wcast-align -Wstrict-prototypes \
  -Wmissing-prototypes -Wmissing-declarations -Wredundant-decls -Wno-long-long \
  micro_inetd.c -o micro_inetd          # 零警告通过

# 配方固化（conan create）
make -j1 CC=<conan conf 提供的 clang> CFLAGS="<上游警告集 + -fPIE -pie -D_FORTIFY_SOURCE=2>" LDFLAGS=""
# 安装：conan copy() 直接安装 bin/micro_inetd + share/man/man1/micro_inetd.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 install 目标不可用 | 硬编码 /usr/local/bin，无 mkdir -p，无 DESTDIR/PREFIX 支持 | 不驱动 `make install`，package() 用 conan copy() 直接安装 |
| 2 | 上游 `LDFLAGS = -s` 链接期 strip | 提前 strip 与发布流水线符号处理冲突 | 命令行覆盖 `LDFLAGS=""` |
| 3 | CC=cc 在 OHOS 不存在 | 上游默认 SystemV/BSD 假设 | 命令行覆盖 `CC=<clang>`，从 Conan conf 获取（R33） |

## 源码修改

无补丁。上游源码零修改编译通过：
- `#include <memory.h>`（非标准但 musl 提供）原样可用
- `USE_IPV6` 自动启用（AF_INET6 + IN6_IS_ADDR_V4MAPPED 均定义）
- signal/dup2/execv/waitpid 全部为 POSIX 接口，musl 完整支持

## 依赖版本

- 无第三方依赖（仅 libc/musl，系统自带）

## 验证结果

```bash
# 探索阶段产物验证
readelf -h micro_inetd   # ELF64 / AArch64 / DYN (PIE)
readelf -l micro_inetd   # INTERP /lib/ld-musl-aarch64.so.1
readelf -d micro_inetd   # NEEDED libc.so；FLAGS BIND_NOW；FLAGS_1 NOW PIE（全 RELRO）

# conan create + test_package（socket→stdin/stdout 契约测试）见 test-report
```

## test_package 设计（inetd 契约验证）

在无 systemd/inetd 的目标环境验证"已连接 socket 作为子进程 stdin/stdout"契约：

1. **请求/响应**：micro_inetd 派生 `/bin/cat`（echo 模式），客户端写入→读回必须一致（stdin/stdout 双向都接 socket）
2. **退出状态**：子进程退出码经 waitpid 收割，僵尸不残留（/proc/<pid> 消失）
3. **并发连接**：4 个连接同时打开、交替读写，各自独立回显正确
4. **重复连接**：服务进程存活期间顺序发起多轮连接（验证 nowait 语义 + SIGCHLD 收割循环）
5. **非法命令处理**：`micro_inetd <port> /nonexistent` 派生失败 → 连接立即 EOF（读返回 0）
6. **参数不足**：`micro_inetd`（无参数）→ usage 退出码 1

进程/端口清理策略（无 root、无系统服务管理器）：
- 端口：仅绑定 127.0.0.1 上的非特权高端口（>1024，运行期从系统申请），micro_inetd 退出即释放（SO_REUSEADDR 由其自带）
- 进程：测试驱动 fork 子进程运行 micro_inetd（前台），结束时 SIGTERM→限时 waitpid，超时 SIGKILL 兜底；任何路径都经同一清理函数退出（atexit 不依赖）
- 无后台残留：验证方式为 waitpid 成功返回 + kill(pid, 0) 返回 ESRCH

## 注意事项

- micro_inetd 监听 `::`（v6 any，v4-mapped）而非仅 127.0.0.1；测试环境为隔离容器，实际部署需自行注意暴露面
- 上游 2014-08-14 为最终版本（Homebrew 已标 unmaintained/deprecated，acme.com 原站仍在线）
