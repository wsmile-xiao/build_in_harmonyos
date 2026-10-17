# sockperf 3.7 适配笔记

## 编译环境
- 构建系统: autotools（tag 3.7 归档无预生成 configure，构建期 autoreconf -fi 自举）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（OHOS aarch64 交叉，clang 15.0.4）
- 状态: built

## 编译步骤

1. `conan create` 驱动：`source()` 下载 GitHub tag 3.7 tarball（官方 URL，sha256 校验）。
2. `build()`：
   - 补写 `build/current-version` = "3.7"（tag 归档缺失该文件，configure.ac 的 esyscmd 读它定 AC_INIT 版本；upstream versioning.sh 在打 tag 时由 git describe 生成同一字符串）；
   - `_prepare_autotools_env`（AUTOCONF/AUTOM4TE/SED 指向 PATH 实际工具，abiword 合入模式）；
   - `autoreconf -fi` 自举（tool_requires automake/1.18 + libtool/2.5.4——CI worker 无自举工具链）；
   - 构建期正则移除生成 configure 中 `(umask 077 && …)` 包裹（E114，HMDFS setgid）；
   - 聚合 env 脚本 `/data/service/hnp/bin/bash` 文本替换为 `/bin/sh`（E386/经验汇总 §12.70①）；
   - `configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（bootstrap 提供的现代 config.sub 可解析 ohos triplet；host 必须归一化为 aarch64，否则 configure 报 "has not been ported"）；
   - `make -j1`（无注册测试，无 make check 目标可执行）。
3. `package()`：`make install` → `bin/sockperf` + man 页。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档缺 `build/current-version`，autoreconf 时 esyscmd 取空版本 | 归档不含发布期生成的版本文件 | 构建期补写 "3.7"（与 tag 语义一致） |
| 2 | CI 无 automake/libtool，无法自举 | CI worker 环境限制 | tool_requires automake/1.18 + libtool/2.5.4（cliquer/abiword 先例） |
| 3 | `AC_SEARCH_LIBS([backtrace],[execinfo],…,AC_MSG_ERROR)` 硬检查 | musl 系通常缺 backtrace | 设备 clang 探针实证 OHOS musl libc 原生提供 backtrace()（bt.c 链接运行成功），configure 直接命中 libc，无需 libexecinfo 包 |
| 4 | E114/E386 常规两坑 | HMDFS setgid + profile 钉死 hnp bash | 同 toppred/trf 的构建期修复（§12.70①/§12.73③） |

## 源码修改

无补丁文件（patches 为空）。构建期：补写版本文件 + 对自举生成物 configure 做 E114 替换（均不进源码树 diff）。

## 依赖版本

无外部依赖（librt/libpthread/libdl/backtrace 均由 OHOS musl libc 提供）。

## 路径 A/B 判断（2026-09-20 GLM-63 复核）

**判定：纯路径 A，不触发路径 B。** 依据：本任务的技术点全部复用知识库已有条目（E114 configure umask 077、E386/§12.70① profile 钉死 hnp bash、E007 家族 autoreconf 自举与 triplet、cliquer/abiword 自举先例），无跨仓库复用的新知识增量：tag 归档缺 `build/current-version` 属上游单库打包特性，TR1/affinity/timeval/stdio 四处移植均为 musl/libcxx 通用适配的常规实例，查重不构成新草稿门槛。已穷尽方案仍无法适配的部分不存在（构建、测试、打包全通过）。

## 验证结果

### 上游测试五维账本（R51/§10.1 口径）

- `N_static` = 0：上游无 automake TESTS/check_PROGRAMS 注册（tests/Makefile.am 仅 test_SCRIPTS 安装声明）
- `N_registered` = 0（--enable-test 默认关闭且其产物只是安装脚本，无测试驱动）
- `N_executed` = 0（如实申报；上游无注册套件）
- 未执行 = 0
- 上游测试资产（实测口径）：6 个（tests/ 下 avner-test.sh、avner-master-test.sh、vma_multiplexers_test.sh、vma_perf_envelope.sh、avner-analyze.awk、avner-test-orig）——全部为需独立服务器 IP 的人工对端基准脚本（如 avner-master-test.sh 用法 `$0 <Server-IP>`），绑定 Mellanox VMA 私有栈变量，交叉单机环境不可整体复现；行为覆盖由消费者回环测试补位
- `N_consumer` = 1（test_package/test.sh：TCP 回环 server+ping-pong 实测，断言 4 处）

```bash
# conan create 内真实执行 test_package：
# ALL CONSUMER TESTS PASSED（日志见 .ci_logs/）
```

### 消费者测试

test_package/test.sh（conanrun 环境，TCP 回环——OHOS 仅禁 AF_UNIX bind，TCP 可用）
- 断言 1：sockperf server 启动且存活
- 断言 2：`sockperf ping-pong -i 127.0.0.1 --time 2` 退出码 0
- 断言 3：客户端输出含 Summary 汇总
- 断言 4：实测调用数 > 0

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/sockperf | ~1MB | 网络延迟/吞吐基准 CLI |

## 注意事项

- 上游无注册测试（N_static=0），以 TCP 回环端到端消费者测试补位；tests/ 人工基准脚本不打包。
- commands.json（软件级）声明 sockperf 为 tool 类型。
- 语言预检：perl 占 52% 为辅助脚本，按构建系统/manifest 判 cpp（c↔cpp 兼容族）。
---

**编译结束**: 2026-09-20 03:09
**最终状态**: built
