# xpa 2.1.20 适配笔记

## 编译环境
- 构建系统: autotools（发布归档自带预生成 configure，无需 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS aarch64 交叉，clang 15.0.4）
- 状态: built

## 编译步骤

1. `conan create` 驱动：`source()` 下载 GitHub tag 2.1.20 tarball（官方 URL，sha256 校验）。
2. `build()`：
   - 构建期正则移除预生成 configure 中 `(umask 077 && …)` 包裹（E114，HMDFS setgid，同 sockperf）；
   - 聚合 env 脚本 `/data/service/hnp/bin/bash` 文本替换为 `/bin/sh`（E386/经验汇总 §12.70①）；
   - `configure --build=aarch64-unknown-linux-gnu`（**不带 --host**：自带 config.sub 不认 OHOS 三元组会误判交叉编译并跳过 AC_RUN_IFELSE 运行时探测，E007 同形态，GLM-63/Q-10 实测）；
   - in-source 布局（`basic_layout(src_folder=".", build_folder=".")`）：生成的 Makefile 不支持 VPATH，out-of-source 报 `No rule to make target 'Makefile.in'`；
   - Tcl 探针在无 tclConfig.sh 环境自动降级（no_tcl=true），X11 探针 AC_PATH_XTRA 找不到 X 时 have_x=no，均无需显式禁用；
   - `make -j1`（R9/E074：并行 make 触 HMDFS jobserver fifo EPERM）；
   - `make -j1 testall`（上游测试入口，编出 ctest/stest/rtest）+ 执行 `run_upstream_tests.sh`（stest 常驻 + xpaset/xpaget 往返 + ctest -g -l 3，取自官方 doc/examples.html；xpans 后台化启动 + trap 清理）。
3. `package()`：`make install INSTALL_ROOT=<package_folder>`（xpa Makefile 忽略 DESTDIR、只认自有变量 INSTALL_ROOT，Makefile.in:35-43）→ `lib/libxpa.a` + `include/xpa.h` + `bin/`（xpaget、xpaset、xpans、xpaaccess、xpamb、xpainfo）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E114/E386 常规两坑 | HMDFS setgid + profile 钉死 hnp bash | 构建期修复（§12.70①/§12.73③），同 sockperf/toppred |
| 2 | dlcache sidecar `KeyError: 'references'` | 缓存元数据被写成旧形态 | 按正确形态预置 `{"references":{...},"timestamp":N}`（§12.39①②） |
| 3 | `Invalid configuration 'aarch64-unknown-linux-ohos'` | 自带 config.sub 不认 OHOS 三元组 | 删 `--host`，只留 `--build=aarch64-unknown-linux-gnu`（E007 forbid 形态） |
| 4 | `No rule to make target 'Makefile.in'` | 生成的 Makefile 不支持 VPATH | in-source 布局 `basic_layout(src_folder=".", build_folder=".")` |
| 5 | `mkdir: cannot create directory '//include': Permission denied` | Makefile 忽略 DESTDIR、只认 `INSTALL_ROOT`（Makefile.in:37 前缀到 prefix/exec_prefix） | `autotools.install(args=["INSTALL_ROOT=<package_folder>"])`（B 草稿机制） |
| 6 | 上游测试脚本 `timed out after 30s: ./xpans` | xpans 是常驻 nameserver，前台启动永不退出 | 后台化 + `kill -0` 探活 + trap 清理（不留守护进程） |
| 7 | `FAIL: ctest produced no XPAGet result` | 断言词错误：ctest 实际输出 `received from XPA:xpa` | 断言改为 grep `received from` |
| 8 | `test.sh: No such file or directory`（test() 阶段） | Conan2 test() 的 CWD 不在 test_package 源目录 | 以 conanfile `__file__` 绝对路径引用 test.sh |
| 9 | `FAIL: xpans not found in PATH`（test_package） | 静态库默认 `cpp_info.bindirs=[]`（include/lib 有默认、bin 没有）⇒ VirtualRunEnv 产出空 conanrunenv | `package_info()` 显式 `self.cpp_info.bindirs = ["bin"]`（机制已入 B 草稿库通用池） |

| 10 | `XPA$ERROR: no response from server during handshake (QCXPA:point)`、`FAIL: XPAGet got=1 payload=(null)` | 子进程事件循环写成 `XPAPoll(50, -1)`；上游 `doc/pod/xpapoll.pod` 逐字规定 **maxreq < 0 时不处理任何事件**、只返回 pending 数 ⇒ 循环 200×50ms 空转后 `XPAFree()+_exit(0)`，服务端从未应答。迷惑点：第 4 组断言「子进程退出码 0」反而**不失败**，容易被误读成网络/ nameserver 问题 | 改 `XPAPoll(50, 0)`（0 = 处理所有当前挂起请求）；实测 4 组断言全过、`ALL CONSUMER TESTS PASSED` |
| 11 | `L0k: commands.json type should be "tool" (R38)` → `xpa/2.1.20 (L0 gate: commands_json_r38)`、W3 直接阻塞 | 软件级 `commands.json` 把交付标成 `type: "library"`，但配方 `package_info()` 声明了 `bindirs=["bin"]` 且实际装了 `xpans`/`xpaget`/`xpaset`/`xpaaccess`/`xpamb` 等 CLI ⇒ `detect_bindirs.py` 返 1、`build_and_test.sh` 的 L0k（684-775 行）按 R38 要求 `type=="tool"` | 改 `type: "tool"`（对齐 `templates/commands.json.template` 与已合包形态），name/versions 两项判据同步核；改后 **W3 本地 CI 模拟通过** |
## 源码修改

无补丁（patches 为空）；全部适配在配方与测试脚本层完成。

## 依赖版本

无外部依赖（socket/nsl/dl/pthread 由 OHOS musl libc 提供；Tcl/X11 自动降级关闭）。

## 验证结果

### 上游测试五维账本（R51/§10.1 口径）

- `N_static` = 3：`Makefile.in:154 TESTPROGS = ctest stest rtest`，注册入口 `testall:`（Makefile.in:158）；上游没有 automake TESTS、没有 check 目标（不得声称跑过 make check）
- `N_registered` = 3（testall 目标注册的三个测试程序）
- `N_executed` = 2（ctest 迭代 + xpaset/xpaget/stest 往返，均在 build() 内真实执行并留日志）
- 未执行 = 1：`rtest` **本窗实测**（2026-09-22，构建目录内 `./stest smoke & sleep 3; timeout 30 ./rtest rperf smoke`）⇒ 30s 不返回、由 timeout 终止 `rc=124`：它先以 `XPANew` 建自己的访问点（`rtest.c:135`）、随后进入**常驻事件循环**，且启动即报 `XPA$WARNING: xpans needs to be running on this machine` 并要求手工 `xpaset -p <method> -nsconnect` 注册 ⇒ 纳入 `build()` 会挂到超时而非给出结果；上游自身的自跑目标 `smoke: ctest stest`（`Makefile.in:247`）**同样不含 rtest**。按"注册 3 / 执行 2 / 未执行 1"如实申报，**不从分母删除**。（更正：此前把原因写成"走 `xpap.h` 的 RPC/sunrpc 路径"**不成立**——`xpap.h` 只是上游总括头，已执行的 `ctest.c:10` 同样 include 它，且本包 `--disable-shared --enable-static` 不链 sunrpc；该说法已撤回。）
- `N_consumer` = 1（test_package/xpa_consumer.c：fork 双进程模型，4 组断言）

### 消费者测试

test_package（CMakeToolchain+CMakeDeps 编译消费者程序，fork 双进程 + 打包版 xpans 端到端）
- 断言 1：子进程 XPANew 注册 access point 成功（非 NULL）
- 断言 2：父进程 XPAGet 经 nameserver 环回命中 access point 且 send 回调 payload 正确
- 断言 3：XPASet 驱动 recv 回调触发且收到客户端载荷
- 断言 4：XPAFree 清理后正常退出（退出码 0 + ALL CONSUMER TESTS PASSED 标记）
- 形态说明：XPA 服务端回调只在自身事件循环内被服务，同进程自建访问点再 XPAGet 必自锁，
  故消费者采用 fork 双进程（子进程 XPANew+XPAPoll，父进程 XPAGet/XPASet 断言，pipe 回传结果），
  与上游 stest/ctest 的两进程形态同构；test.sh 负责启动打包版 xpans 并在退出时清理

## 路径 A/B 判断（2026-09-22 DS-31 定稿，Q-10 判定留痕在登记表）

**判定：路径 B（贡献创新），B草稿 = DRAFT-xpa-2.1.20-legacy-makefile-install-root-override。**
机制：Tcl 系老式 Makefile 无 DESTDIR 约定、只认自有 INSTALL_ROOT 变量（Makefile.in:35-43 实证），
conan 默认 `make install DESTDIR=<pkg>` 被静默忽略、落点炸到根级 `//include`；改用上游预留的
`INSTALL_ROOT=<package_folder>` 完成暂存。查重：E098/E108/M13 是安装命令缺失族（Error 127），
M7 是运行期 prefix 烧死，E011/E114 是权限位语义——均不同签名/解法 ⇒ create。
（GLM-63 早期"纯路径 A"判定基于当时问题面；Q-10 在 INSTALL_ROOT 修复后已按 B 判定=create
留痕登记表，本节随之更新。）草稿随本 PR 原子提交，正文含 3+2 行最小声明。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libxpa.a | ~300KB | 消息传递库（静态） |
| bin/xpans | ~100KB | nameserver 守护 |
| bin/xpaget、xpaset、xpaaccess、xpamb | 各~100KB | 客户端工具集 |

## 注意事项

- 上游测试入口是 `make testall`（3 个测试程序），无 make check；N_executed=2（ctest+往返），
  rtest 未执行原因见五维账本。
- commands.json（软件级）声明 xpa 为 library 类型（含 bin 工具）。
- `package_info()` 显式声明 `cpp_info.bindirs=["bin"]`：静态库默认 bindirs 为空列表，否则
  test_package/下游经 PATH 找不到 xpans/xpaget/xpaset（机制已入 `经验文档/B草稿库/` 通用池）。

## 对话记录

> #1/#2 转录自交接包 `~/tmp/uc2/handoff/xpa-2.1.20/README-handoff.md` 与各窗口日志（来源已标注）；
> #3 为本窗 Q-21 亲历实测。

### 对话 #1 [2026-09-21→09-22 GLM-63/Q-10]

- 问题: conan create 首轮 G2 FAIL 的第一条真实错误是 conandata 残留 `ghfast.top` 镜像 URL 读超时（非配方缺陷）
- 操作: 按 §9 恢复官方 URL、按 §12.3 用官方 tarball 预置共享 dlcache，并修正 sidecar 的
  `references` 结构（E017/§12.39 家族）
- 结果: 下载阶段通过；后续暴露 4 个真实阻塞（`--host` 三元组、in-source、`INSTALL_ROOT`、consumer API 签名）

### 对话 #2 [2026-09-22 DS-31]

- 问题: ①自带 config.sub 不认 OHOS ⇒ `Invalid configuration 'aarch64-unknown-linux-ohos'`；
  ②生成的 Makefile 不支持 out-of-source ⇒ `No rule to make target 'Makefile.in'`；
  ③老式 Makefile 忽略 DESTDIR、只认自有 `INSTALL_ROOT` ⇒ `mkdir: cannot create directory '//include'`；
  ④原 `xpa_consumer.c` 从未编译过（`XPANew` 少一参、`XPAGet` 参数序错位），且同进程自建访问点再
  `XPAGet` 在 XPA 里必自锁（服务端回调只在自己的事件循环内被服务）
- 操作: 删 `--host` 只留 `--build`（E007 forbid 模式口径）；`basic_layout(src_folder=".", build_folder=".")`；
  `autotools.install(args=["INSTALL_ROOT=<package_folder>"])`；消费者重写为 **fork 双进程**；
  `build()` 接入 `make -j1 testall` + `run_upstream_tests.sh`（stest 常驻 + xpaset/xpaget 往返 + `ctest -g -l 3`）
- 结果: `conan create` 主体通过、上游往返实测通过；剩一处 `xpans` 前台常驻被自写 `run_bounded` 判超时未解

### 对话 #3 [2026-09-22 Q-21 本窗]

- 问题: 首轮真跑 test_package 失败 3 条断言——
  `FAIL: XPAGet got=1 payload=(null) (XPA$ERROR: no response from server during handshake (QCXPA:point))`、
  `FAIL: XPASet got=0 ()`、`FAIL: receive callback did not observe the payload`。
  同时发现上一轮 `conan-verify` 的 G2 是 **conan binary cache 命中**（日志 4 处 `- Cache`、
  无 `Calling build()`）⇒ 该份日志不能充当"上游测试在 build() 真实执行"的证据
- 操作: ①查上游 `doc/pod/xpapoll.pod` 确认 `XPAPoll(int msec, int maxreq)` 语义——
  `maxreq < 0` 表示**不处理任何事件**、只返回挂起数，故子进程 200×50ms 空转后 `XPAFree()+_exit(0)`，
  父进程握手必然无应答（而"子进程退出码 0"这条断言反而通过，方向极易判错）；改 `XPAPoll(50, 0)`。
  ②`conan remove "xpa/2.1.20@ohpcd/stable" -c` 强制源码重建，再跑 conan-verify（gate 8000MB + build-slot 独占槽）
- 结果: 真重建日志内 `Building from source` + `Calling build()` + `RUN: make -j1 testall` +
  `UPSTREAM XPA TESTS PASSED: stest + xpaset/xpaget round trip + ctest -g -l 3 (3 XPAGet result lines)`；
  test_package `OK: XPAGet round trip, 32 bytes via send callback`、
  `OK: XPASet delivered 32 bytes to the receive callback`、`ALL CONSUMER TESTS PASSED`；
  G0/G1/G2/G3/G4 全 PASS、`VERIFY_RC=0`。conandata 活文件已逐行核对为官方 URL +
  sha256 `854af367…4786a`（镜像注入已恢复，非仅凭日志"已恢复"字样）。
---

**编译结束**: 2026-09-22 16:21
**最终状态**: built
