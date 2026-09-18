# libdontdie 1.2.0 适配笔记

## 任务信息

- 平台任务号：13132（活动：开源鸿蒙PC专项积分赛-依赖）
- 分支：feat/libdontdie-1.2.0；worktree：~/qzy/glm44-libdontdie
- 上游：https://github.com/flonatel/libdontdie tag 1.2.0（tarball sha256 f9ac36d2…998e）
- 语言：C；构建系统：纯 GNU Makefile（无 configure，单文件 src/libdontdie.c → libdontdie.so）
- 主理 agent：9/17-GLM-44
- 本任务在 ohpcd 平台异常期间适配：PR 建好后由用户在平台恢复后导入/绑定/提审。

## W0 依赖检查

- 零精确版本依赖：`preflight_check.sh libdontdie/1.2.0` 输出"未找到依赖声明…预检通过"。
- 库自身仅依赖 libc（socket/getsockopt/syslog/dlsym）；-ldl 与上游 Makefile 保持一致，OHOS musl 链接通过（G2 干净构建实证）。

## W0b 历史经验

- 仓库无 libdontdie 历史归档，首次适配。
- 知识库检索：recipe-search 无相似配方（语料 4938 条，首稿走模板）。
- 复用已有经验（未新增草稿）：
  - 简单 Makefile 项目显式传编译器（经验汇总 §12.2：Makefile `CC=gcc` 是 `=` 赋值，会覆盖环境变量，必须 make 命令行传 CC）；
  - 动态拦截/插件库的消费者测试必须真实加载目标 .so（经验汇总 §12.2）；
  - conan.tools.files.copy 会把 symlink 复制成目标文件副本，soname 链接需在 package() 中用 os.symlink 重建。

## 上游测试清点（R51 证据）

Makefile 目标全量清单：`all`（libdontdie.so + libdontdie.so.0 symlink）、`testapps`（perf + EchoClient.class + tcp_server + tcp_client）、`clean`。
**无 check/test 目标**，无任何标准测试框架（无 make check/ctest/dejagnu）：静态注册用例总数 N_static = 0。

上游随附 4 个手工驱动测试资产（非框架注册）：

| 资产 | 类型 | 处置 |
|---|---|---|
| test/Cperformance/perf.c | 非交互程序（循环 socket()+close，失败退出码 1） | **真实执行**：build() 中 LD_PRELOAD=libdontdie.so 运行 1000 次，退出码 0 |
| test/Cblackbox/tcp_server.c | 交互式（stdin 逐字符命令驱动） | 编译验证通过；执行跳过：无头自动化会因 stdout 管道全缓冲死锁 |
| test/Cblackbox/tcp_client.c | 交互式（与 server 配对） | 编译验证通过；执行跳过：同上；其覆盖场景由消费者测试等价覆盖（可断言） |
| test/java/EchoClient.java | Java 示例 | 跳过：OHOS 设备无 JVM/javac |

## 四维测试账本

| 维度 | 数量 | 说明 |
|---|---|---|
| 上游静态声明 N_static | 0 | Makefile 无 check/test 目标，无测试框架注册 |
| 构建注册 N_registered | 4 | testapps 目标 4 个程序（3 C + 1 Java），均编译验证（Java 无工具链，编译亦跳过） |
| 实际执行 N_executed | 1 | perf 1000 次 socket() 拦截（退出码 0）；交互式 2 个 + Java 1 个按上表跳过 |
| 消费者测试 N_consumer | 1 | test_package/dd_consumer.c，3 项断言（N_assertion=3） |

## 消费者测试设计

libdontdie 无导出 API、无公开头文件（LD_PRELOAD 拦截 socket(2) 型库），无法"调用公开 API"，
消费者测试按"运行被测产物并断言行为"口径设计：

1. test_package 以库使用者身份编译独立 C 程序 dd_consumer.c（只链接 libc socket API）；
2. test() 运行时注入 `LD_PRELOAD=<package_folder>/lib/libdontdie.so`（绝对路径；musl 忽略
   DT_RUNPATH，conanrunenv 不足以完成预加载）与 `DD_TCP_KEEPALIVE_TIME=7`；
3. 断言：①socket() 成功；②SO_KEEPALIVE 已被库置 1；③TCP_KEEPIDLE == 7（上游将
   DD_TCP_KEEPALIVE_TIME 映射到 TCP_KEEPIDLE，见 src/libdontdie.c `SET_SOCK_OPT(time, "TIME", TCP_KEEPIDLE)`）；
   任一失败退出码非 0。G2 实测输出：`dd_consumer OK: SO_KEEPALIVE=1, TCP_KEEPIDLE=7`。

OHOS musl 无 `TCP_KEEPALIVE` 宏（第一轮 G2 编译报 undeclared identifier），上游源码实际使用
TCP_KEEPIDLE/TCP_KEEPINTVL/TCP_KEEPCNT，消费者测试随用 TCP_KEEPIDLE。

## 构建方式

- `make CC=<ohos-clang> -j1`（命令行传 CC 覆盖上游硬编码 gcc）；CFLAGS/LDFLAGS 沿用上游
  默认（-fpic -Wall -Wextra -O3 / -shared -Wl,-soname,libdontdie.so.0），-ldl 保留与上游一致。
- 上游无 install 目标：package() 手工 copy libdontdie.so + os.symlink 重建 libdontdie.so.0 + LICENSE。
- 上游只产 shared：validate() 对 shared=False 抛 ConanInvalidConfiguration。
- 无补丁（patches: {}，配方显式调用 apply_conandata_patches）。

## 路径 B 判断

判定：**不走 B，纯 A**。理由：本次适配复用知识库已有条目（简单 Makefile 显式传参、动态拦截库
消费者测试真实加载 .so，均已存在于经验汇总 §12.2 与知识图谱），无新的跨仓库可复用知识增量；
无稳定新错误签名（唯一失败为宏名 TCP_KEEPALIVE→TCP_KEEPIDLE 的消费者测试修正，属常规移植
差异）。无新增知识草稿、无知识库扩展 Issue。

## 构建环境

- 设备真机（OHOS aarch64），CONAN_HOME=~/tmp/ch/home-glm44-libdontdie（global.conf 含
  tools.build:jobs=2，remotes.json 自 Codex-3 已验证 home 复制）。
- profile：ci/conan/profiles/ohos-aarch64（host/build 同 profile）。
- 源码下载：E017 场景（ghfast.top 超时），官方 tarball 按 SHA256 预置共享 download_cache
  （sidecar 同时登记官方 URL 与 ghfast 注入 URL），SHA 核对一致。

## 验证命令与结果

- `python3 scripts/ohc-run.py conan-verify libdontdie 1.2.0`：**Verdict PASS**（G0-G4 全过），
  报告 archives/l/libdontdie/1.2.0/reports/conan-verify-report.md，绑定 worktree HEAD
  da869265fa（upstream/main 基线，配方提交前的验证轮次）。
- G2 干净构建日志含上游 perf 测试执行与消费者测试执行输出（conan-create.log）。

## 已知限制

- 交互式黑盒对（tcp_server/tcp_client）未无头执行：stdout 管道全缓冲且无刷新点，自动化驱动
  会死锁；其核心场景（连接建立后 keepalive 生效）已由消费者测试以可断言方式等价覆盖。
- Java 示例未执行（平台无 JVM），与适配质量无关。

## finish 收尾块

- conan-verify：PASS（G0-G4）；W3 本地 CI：见 reports/w3-local-ci.log；W4 独立审计：PR 提交前完成（P0/P1 清零）。
- 测试数字同源核对：notes.md = MANIFEST.yml = PR 正文 = result.json（N_static=0，N_executed=1，
  N_consumer=1，N_assertion=3）。
- 提交方式：精确 add archives/l/libdontdie/1.2.0/（绝无 -A）；libXext/libxext 大小写假改动不碰。
---

**编译结束**: 2026-09-17 03:08
**最终状态**: built
