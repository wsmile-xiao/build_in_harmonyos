# pnscan 1.14.1 适配笔记

## 任务信息

- 平台任务号：9620（活动：开源鸿蒙PC专项积分赛-依赖）
- 分支：feat/pnscan-1.14.1；worktree：~/qzy/glm44-pnscan
- 上游：https://github.com/ptrrkssn/pnscan tag v1.14.1（tarball sha256 d7c56990…3cf8）
- 语言：C；构建系统：autotools（autoconf 2.69 预生成 configure；build-aux 无 config.guess/config.sub，无 AC_CANONICAL_HOST）
- 主理 agent：9/17-GLM-44
- 本任务在 ohpcd 平台异常期间适配：PR 建好后由用户在平台恢复后导入/绑定/提审。

## W0 依赖检查

- 零精确版本依赖：pthread/socket/nsl 由 AC_SEARCH_LIBS 探测，OHOS musl 的 pthread/socket 在 libc 中，configure 实测探测通过（conan-create.log：checking for socket... yes）。

## W0b 历史经验

- 仓库无 pnscan 历史归档，首次适配。recipe-search 无同包配方。
- 复用已有经验：
  - E386（HMDFS getcwd 缺陷）：autoconf re-exec 经 CONFIG_SHELL（登录 hnp bash 经 conanbuildenv 进入构建环境）触发 getcwd 失败——本配方用显式 source conanbuildenv-*.sh + `env -u CONFIG_SHELL SHELL=/bin/sh` 逐命令路由（经验汇总 §12.38 首选修法的自管变体）；
  - E011/E114（config.status subs1.awk Permission denied）：autoconf 2.69 以 `(umask 077 && mktemp/mkdir)` 创建临时目录，0700 权限在 HMDFS 上不可写——build 时 `sed 's/umask 077/umask 022/g' ./configure`（保留目录创建逻辑，仅放宽权限位）。

## 上游测试清点（R51 证据）

Makefile.in 定义 `check: check-simple check-verbose check-hostname check-response check-response-fail`，共 5 个测试子目标；每个子目标启动上游自带 t_listen 回显守护进程（随机端口，10 秒 alarm 超时）并对 127.0.0.1 发起真实扫描。check-valgrind 需 valgrind 工具，不在 check 依赖链，不计入。

- 静态声明 N_static = 5；构建注册 N_registered = 5；实际执行 N_executed = 5（build() 内 `make check` 真实执行，5 个子目标全部以 make 退出码 0 通过）。

注意（如实记录）：pnscan main 以 pthread_exit(NULL) 结束（退出码 0），-r 响应不命中也不产生非零退出码，故 check-response-fail 与 check-response 一样以 make 退出码判定通过——这是上游测试语义的固有弱点；消费者测试以显式断言补强（要求命中报告存在）。

## 四维测试账本

| 维度 | 数量 | 说明 |
|---|---|---|
| 上游静态声明 N_static | 5 | Makefile.in check 目标 5 个子任务 |
| 构建注册 N_registered | 5 | 同上（make check 可执行目标） |
| 实际执行 N_executed | 5 | build() 内 make check 真实执行（退出码 0） |
| 消费者测试 N_consumer | 1 | test_package/dd_consumer.c（N_assertion=3） |

## 消费者测试设计

pnscan 是扫描工具（无库产物），消费者测试按"运行被测二进制并断言行为"口径：dd_consumer.c
真实执行打包产物 bin/t_listen（读出监听端口）与 bin/pnscan -r "Hello" 127.0.0.1 <port>，
断言 ①t_listen 输出合法端口、②pnscan 退出码 0、③扫描报告包含 "Hello, World!" banner。

## 构建方式

- 显式 source AutotoolsToolchain 生成的 conanbuildenv-*.sh 后，以
  `env -u CONFIG_SHELL SHELL=/bin/sh` 前缀顺序执行 ./configure / make / make check
  （绕开 conan 聚合 env 对 SHELL 的 hnp bash 注入，E386）。
- configure 前对 ./configure 执行 sed 's/umask 077/umask 022/g'（E011/E114，HMDFS 临时目录权限）。
- 交叉参数 --host/--build 均为 aarch64-unknown-linux-gnu（上游 config.sub 缺失，triplet 仅形式）；
  实际编译器经 env 的 CC=/data/service/hnp/bin/clang（configure 实测）。
- package() 手工复制 pnscan、t_listen（上游 test 守护进程，消费者测试复用）与 LICENSE。

## commands.json（R38，命令行工具）

- install_commands：cp pnscan/t_listen 到 ${bindir}/。
- test_commands：pnscan -r "Hello" 127.0.0.1 `t_listen`（上游 check-response 等价场景）。

## 路径 B 判断

判定：**纯 A**。本任务的 E386/E011 处置均为已有知识条目的复用与参数化（无新错误签名、无跨仓库
新增增量）；构建期对 configure 的 umask sed 属单库构建脚本处理，不构成可跨仓库复用的新知识。
无新增知识草稿、无知识库扩展 Issue。

## 构建环境

- 设备真机（OHOS aarch64），CONAN_HOME=~/tmp/ch/home-pnscan（global.conf: tools.build:jobs=2，
  remotes.json 自 Codex-3 已验证 home 复制）；profile ci/conan/profiles/ohos-aarch64。
- 源码下载：官方 tarball 按 SHA256 预置共享 download_cache（E017 ghfast 超时防御，sidecar 双 URL）。

## 验证命令与结果

- `python3 scripts/ohc-run.py conan-verify pnscan 1.14.1`：**Verdict PASS**（G0-G4），
  报告 archives/p/pnscan/1.14.1/reports/conan-verify-report.md。
- 修试验证轮次：v7 E386（getcwd）→ v9 显式 env 通过 configure → v10 E011（subs1.awk）→
  v11 umask sed 修正后 G2 全过（含 make check 5 场景与消费者测试）。

## 已知限制

- check-response-fail 的上游语义无失败断言（pnscan 退出码恒 0），如实记录；反向场景由消费者
  测试断言补强。

## finish 收尾块

- conan-verify：PASS（G0-G4）；W3 本地 CI：见 reports/w3-local-ci.log；W4 独立审计：提交前完成（P0/P1 清零）。
- 测试数字同源核对：notes.md = MANIFEST.yml = PR 正文 = result.json（N_static=5，N_executed=5，
  N_consumer=1，N_assertion=3）。
- 提交方式：精确 add archives/p/pnscan/1.14.1/（无 -A）；libXext/libxext 大小写假改动不碰。
---

**编译结束**: 2026-09-17 04:53
**最终状态**: built
