# 3proxy 0.9.5 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 家族，树内**无** `./configure`）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

根 `Makefile.Linux` 的 `all` 目标把自身 `cat` 成 `src/Makefile.var` 后递归进 `src/`，
由 `src/Makefile.inc` 链接 10 个可执行文件并构建 4 个插件。配方 `build()` 实际做三件事：

1. 从 `tools.build:compiler_executables:c` 取编译器（R33：不读裸环境变量）；
2. 用正则读出 `Makefile.Linux` 里的 `CFLAGS = ...` 原值，在其后追加 `-D_UAPI_LINUX_SOCKET_H`；
3. 执行 `make -f Makefile.Linux CC=<cc> CFLAGS="<上游原值 + 守卫宏>" -j1`（R9：恒 -j1）。
   命令行变量会经 MAKEFLAGS 传递给 `src/` 与各插件子 make，保证每个编译单元都拿到守卫宏。

产物：`bin/` 下 3proxy proxy socks smtpp pop3p ftppr tcppm tlspr udppm mycrypt，
`libexec/3proxy/` 下 StringsPlugin/TrafficPlugin/PCREPlugin/TransparentPlugin 四个 `.ld.so`，
另附 `share/man/` 手册页与 `share/3proxy/3proxy.cfg.sample` 示例配置。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `source()` 报 `BadZipFile: File is not a zip file` | codeload URL 以 tag 名 `0.9.5` 结尾、无扩展名，Conan `get()` 推出文件名 `0.9.5`，`unzip()` 落到 zip 解码器 | `get(..., filename="3proxy-0.9.5.tar.gz")`，让解压选 tar.gz（同 abcmidi 先例） |
| 2 | TransparentPlugin 报 `redefinition of 'struct sockaddr_storage'`（`linux/socket.h:23` vs `sys/socket.h:377`） | OHOS SDK 同时提供 libc 的 `sys/socket.h` 与 kernel uapi 的 `linux/socket.h`；`transparent_plugin.c` 经 `linux/netfilter_ipv4.h → linux/netfilter.h → linux/in.h → linux/socket.h` 把后者拉进来 | **知识条目 E119（macro-guard-skip-header）**：定义 `_UAPI_LINUX_SOCKET_H` 跳过 uapi 头。按 R8/PF5 补丁中不得出现平台宏，改为**配方侧注入中性宏**（`CFLAGS += -D_UAPI_LINUX_SOCKET_H`），实测该插件编译通过 |
| 3 | 本地 W3 的 JC6 报「本 PR 涉及 152 个软件包」 | fork 的 `origin/main` 落后 `upstream/main`，增量基线假阳性（框架已知问题） | `JUNK_PR_DIFF=~/tmp/uc2/3proxy-0.9.5/pr.diff`（只含本包 8 个文件）对齐 CI prdiff 口径复跑 → `JC_ERRORS=0`，不改基线 |
| 4 | `build` 驱动 Step4 报 `Makefile:1: Makefile.var: No such file or directory` | `init-build` 解包只保留了 `src/*`，顶层 `Makefile.Linux` 家族全丢，裸 `make` 落在 `src/Makefile` 上 | 按 `§12.60①` 口径跳过 `build` 驱动，直接走 `conan-verify → finish`（配方自身 `source()` 用 Conan 正确解包，实测 G2 通过） |

## 源码修改

**无补丁**（`conandata.yml` 里 `patches: []`）。两处适配都在配方侧完成：
显式 `filename` 与 CFLAGS 追加中性宏 —— 未改动任何上游源文件，
符合「补丁默认禁止平台宏」（R8 / preflight PF5）。

## 依赖版本

无第三方依赖（`requirements()` 为空，核心只用 libc / libdl / pthread）。
W0：`preflight_check.sh 3proxy/0.9.5` → `预检通过（无依赖需要检查）`，rc=0。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh 3proxy/0.9.5        # rc=0
python3 scripts/ohc-run.py recipe-search 3proxy        # rc=0
python3 scripts/ohc-run.py conan-verify 3proxy 0.9.5    # rc=0（G1/G2/G3/G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py finish 3proxy 0.9.5 built    # W3 本地 CI 通过，.ci-result.json exit_code=0
python3 scripts/ohc-run.py graph validate               # rc=0
```

test_package 消费者测试 **2/2**：
① `3proxy -h` 横幅包含 `3proxy-0.9.5`（上游以退出码 1 返回用法，属预期）；
② 在非特权回环端口启动 HTTP 代理并用真实 TCP 连接打通监听。

## 能力墙判定

**甲**（可等价交付）：非特权端口 `bind`=OK、回环 TCP 连通=OK；
源码 `grep -rn "SOCK_RAW\|AF_PACKET" src/` **0 命中**，核心功能不依赖 raw socket。
受限面只有「特权端口 <1024 bind」与「raw socket」两条（均 `EACCES`，uid=20020105 非特权），
而上游配置里端口任意可写，走非特权端口即可完整降级 —— 与 test_package 检查 ② 的实测一致。

## 知识沉淀（manifest `knowledge_count=2`）

1. 无 configure 的 Makefile 家族：根 `Makefile.Linux` 自拷贝为 `src/Makefile.var` 再递归 `src/`。
2. E119 `macro-guard-skip-header`：`-D_UAPI_LINUX_SOCKET_H` 规避 OHOS SDK
   `sockaddr_storage` 重定义，且按 PF5 走配方侧中性宏注入而非补丁内平台宏。

---

**编译结束**: 2026-10-08 18:10
**最终状态**: built
