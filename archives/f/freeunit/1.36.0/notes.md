# freeunit 1.36.0 适配 notes

## 任务背景
- 目标库：freeunit 1.36.0（NGINX Unit 社区维护分支，动态 Web 应用服务器）
- Issue：#2024 【积分赛】适配 freeunit 库（申请人 gyccc / 队伍 NebulaAGI）
- 上游：https://github.com/freeunitorg/freeunit ，tag `1.36.0`
- 本轮失败域：`evidence` — hmbs 报「无法读取当前 archive 代码树，不能启动真机预检」

## 根因
本轮开始时工作目录为空：git 仓库仅有 origin/upstream 两个 remote 配置、无任何提交，
`archives/` 代码树完全不存在，hmbs 无法读取 archive 启动预检。这是首次 preflight 前的
初始化缺口，不是配方缺陷。
修复：`git fetch upstream main` 恢复代码树到本任务目录，并按守则将 `.hmbs/` 写入
`.git/info/exclude`（幂等）。随后从零创建 freeunit 1.36.0 完整配方。

## 上游构建系统分析（v1.36.0 tag tarball，sha256 f13e9322... 已实测核对）
- 构建系统：NGINX Unit 自研 configure（auto/ 脚本体系），**非** GNU autotools/CMake。
- `sh ./configure --tests` → 生成 `build/Makefile`；`make` 产出 `build/sbin/unitd`
  （守护进程）与测试二进制；`make tests` 保证聚合测试二进制 `build/tests` 存在。
- 模块构建：`./configure <module>`（go/java/nodejs/perl/php/python/ruby/wasm），
  本适配只构建 core unitd（unitd 默认构建，无需模块）。
- CC 读取 `$CC` 环境变量（auto/cc/test），配方按 R33 从 Conan conf 取，回退 clang。

## 上游测试
- **C 单元测试套件（本适配接入的真机测试）**：`src/test/`，聚合入口
  `src/test/nxt_tests.c` 的 main() 依次调用 28 个无条件测试函数 + 条件编译的
  `nxt_cgroup_test`（NXT_HAVE_CGROUP）与 `nxt_clone_creds_test`
  （NXT_HAVE_CLONE_NEWUSER）。任一失败立即 return 1，退出码 0 == 全部通过；
  每个用例成功打印 `<name> test passed`（NOTICE 级）。配方 `_count_tests()` 实读
  configure 产物 `build/include/nxt_auto_config.h` 统计 discovered（28 或 29/30）。
- `make tests` 另产出辅助二进制：utf8_file_name_test（依赖文件系统文件名语义）、
  ncq_test/vbcq_test（队列压力）、unit_app_test/unit_close_test/
  unit_websocket_chat/unit_websocket_echo（libunit 应用协议测试，需运行中的 unitd
  路由进程）。它们不属于 nxt_tests.c 聚合套件，不计入 discovered。
- **Python 集成套件**（`test/`，pytest ~300 用例）：需 root 启动运行中的 unitd 并
  配套 node/python/perl/php/go/ruby/wasm 应用模块运行时，headless 真机预检无法
  满足，未纳入。属环境依赖缺口，已在 MANIFEST.yml 审计中如实说明。

## 计数口径（防"静默通过"伪造）
- HMBS_UPSTREAM_TEST_RESULT：`./build/tests` 以 subprocess 捕获 stdout+stderr；
  discovered/executed 取自配置头文件实读（框架级事实）；rc==0 且输出含
  "test passed" 行 → passed=discovered；rc==0 但 0 个 passed 行 → 判 failed
  （静默跳过陷阱，如实上报 executed=0）；rc!=0 → failed=max(1,失败行数)，
  executed=passed+failed。command 字段 = 真机实际执行的完整命令链
  （configure→make→make tests→./build/tests，` && ` 连接，json.dumps 转义）。
- HMBS_TEST_PACKAGE_RESULT：test_freeunit.sh 两个真实断言（`unitd --version`
  含 "unit version: 1.36.0"、`unitd -h` 帮助输出），脚本非 0 退出时 self.run
  抛错、标记不输出；command 字段为实际执行的 shell 命令。

## 配方文件（本轮全部新增，未 commit）
- `archives/f/freeunit/1.36.0/conandata.yml`：GitHub 官方源 + gh-proxy.com 镜像
  （复用 ci/conan/build_and_test.sh 的 GitHub 映射：镜像在前、官方 URL 兜底），
  sha256 为官方归档实测值 f13e9322...，未改动。
- `archives/f/freeunit/1.36.0/conanfile.py`：validate(Linux/OHOS) + source(get+
  patches) + build(configure --tests → make -j1 [R9] → make tests → ./build/tests
  计数打标) + package(unitd → bin/，LICENSE → licenses/) + package_info。
- `archives/f/freeunit/1.36.0/test_package/`：conanfile.py（VirtualRunEnv +
  2 断言标记）、test_freeunit.sh、MANIFEST.yml（upstream_tests_exist: true +
  完整 upstream_test_audit）。
- `archives/f/freeunit/1.36.0/manifest.yaml`（版本级）、
  `archives/f/freeunit/commands.json`（软件级，L0k/R38：bin/ 有可执行文件必填）。

## 待真机验证
- 工作树保持未提交，等待 hmbs 同步后真机预检复跑。预期：
  1) conan create 构建通过；2) 上游 C 单元套件 discovered≈28-30 全通过；
  3) test_package 2 断言通过。若 configure/编译报 OHOS 兼容错误（如
  auto/os 无法识别 OHOS、缺失平台头文件），下一轮按日志最小补丁修复。

## 第二轮（真机预检 compile 失败 → 已修复）
- 失败：`src/nxt_lib.c:96` `cpu_set_t`/`CPU_ALLOC`/`sched_getaffinity` 等 12 个
  编译错误，make 停在 build/src/nxt_lib.o。
- 根因：真机 `uname -s` 返回 `HarmonyOS`（configure 日志 "configuring Unit
  1.36.0 for HarmonyOS HongMeng Kernel 1.12.0 unknown"），auto/os/test 与
  auto/os/conf 的 case 只认 `Linux`，落入默认分支 → `NXT_LINUX` 未定义 →
  src/nxt_unix.h 中 `#if (NXT_LINUX)` 块被跳过：`_GNU_SOURCE`、`<malloc.h>`、
  `<sys/syscall.h>` 全部缺失。而 auto/sched 的检测代码自带 `#define _GNU_SOURCE`
  故 "Linux sched_getaffinity() found"，NXT_HAVE_LINUX_SCHED_GETAFFINITY 被
  定义后 nxt_lib.c 进入 cpu_set_t 分支，实际编译却无 _GNU_SOURCE，OHOS musl 系
  libc 的 sched.h 不暴露 cpu_set_t/CPU_*。若不修，后续 malloc_usable_size、
  SYS_gettid 等还会连环报错（同属 NXT_LINUX 块）。
- 修复：新增 patches/0001-os-detect-harmonyos-as-linux.patch，把
  `Linux | HarmonyOS | OHOS` 并入 auto/os/test 与 auto/os/conf 的 case，
  使 OHOS 真机走 Linux 分支、定义 NXT_LINUX（_GNU_SOURCE/malloc.h/
  sys/syscall.h 恢复）。conandata.yml 注册该 patch（portability 类）。
  auto/threads 的默认分支与 Linux 分支同为 -lpthread，无需改。
- patch 已在官方归档（sha256 f13e9322... 实测一致）干净副本上 `patch -p1`
  实际应用验证通过；conandata.yml 已用 PyYAML 校验合法。
- 待 hmbs 复跑：确认 nxt_lib.c 编译通过后，后续 make/tests 若再有 OHOS
  兼容问题按新日志继续最小适配。

## 第三轮（真机预检 compile 失败 → 已修复）
- 失败：`src/nxt_thread.c:219` `error: call to undeclared function 'pthread_cancel';
  ISO C99 and later do not support implicit function declarations [-Werror]`，
  make 停在 build/src/nxt_thread.o。
- 根因：OHOS musl 系 libc 的 pthread.h 未声明 `pthread_cancel()`（clang 对隐式
  声明按 C99 禁止 + -Werror 报错）。上游 nxt_thread_cancel() 无条件调用它，
  无 configure feature 检测。
- 运行时影响评估：`nxt_thread_cancel()` 仅由 `nxt_signal_thread_stop()` 调用，
  而信号线程只在事件设施不支持信号事件时启动（nxt_event_engine.c
  `!interface->signal_support`）。OHOS 真机日志显示 epoll 与 signalfd 均
  "found"（NXT_HAVE_SIGNALFD 定义），epoll 接口 signal_support=1，信号线程
  不会启动 → nxt_thread_cancel() 运行时永不执行，缺失时降级为仅打印 debug 日志
  是安全的。
- 修复：新增 patches/0002-pthread-cancel-feature-check.patch，参照上游
  pthread_yield 模式：
  1) auto/threads 增加 `pthread_cancel()` feature 检测（NXT_HAVE_PTHREAD_CANCEL，
     NXT_PTHREAD 链接，_GNU_SOURCE + pthread.h 测试程序）；OHOS 上因声明缺失 +
     CFLAGS 含 -Werror（auto/cc/test）编译失败 → 不定义宏。
  2) src/nxt_thread.c 的 nxt_thread_cancel() 用 `#if (NXT_HAVE_PTHREAD_CANCEL)`
     守卫 pthread_cancel 调用，`#else` 分支仅记录 debug 日志。
- 验证：补丁已在官方归档（sha256 f13e9322...）干净副本上 `patch -p1` 实际应用
  通过（dry-run + 实打均 OK）；conandata.yml 已用 PyYAML 校验合法（patches
  列表含 0001/0002）。
- 待 hmbs 复跑：确认 nxt_thread.o 通过后，若后续还有 OHOS 兼容问题按新日志继续
  最小适配。
