# clips 6.3（上游 6.30）适配笔记

- 分支：`feat/clips-6.3`（worktree `D:\harmonyos\worktrees\clips`）
- 日期：2026-09-08（本机前置 + 真机验证完成）
- issue：待补
- 上游：CLIPS 6.3 系列首发版 6.30（2014-08-16）
  - URL：https://downloads.sourceforge.net/project/clipsrules/CLIPS/6.30/clips_core_source_630.zip
  - sha256：`01555b257efae281199b82621ad5cc1106a395acc095b9ba66f40fe50fe3ef1c`
  - 版本口径：任务版本 6.3 = 6.3 系列首发；上游文件名/源码头注释为 6.30。
    SourceForge 目录只有 6.30/6.31 两档，无 6.3 目录；Debian 打包同源 6.30。

## 真机最终验证结果（2026-09-08，第三轮）

- 设备：OHOS 真机 10.62.134.118（HongMeng Kernel 1.12.0 aarch64）
- 命令：`conan create archives/c/clips/6.3 -pr:h ohos-aarch64 -pr:b
  ohos-aarch64 --build=missing`（隔离 CONAN_HOME，源码离线缓存）
- 结果：**CONAN_CREATE_RC=0**，recipe revision
  `clips/6.3#82cc6cb8935467ae1b3d66bc4f6824ae`
- test_package **10/10 断言 PASS**：CreateEnvironment / EnvBuild×3（claim、
  result、defrule）/ EnvBuild 非法语法拒绝 / EnvAssertString / EnvRun 恰触发
  1 条规则 / 事实列表轮询找到 (result (value ok)) / EnvFunctionCall (+ 2 3)=5
  / DestroyEnvironment(fresh env)
- CLI 端到端：`clips -f2 hello.clp` 输出 CLIPS-CLI-OK，grep 断言通过
- 内存：全程 MemAvailable ~12.7-13.5GB，与 botan3 -j1 任务并发无冲突
  （tools.build:jobs=1 + make -j1 + cmake -j1）

### 消费者用例（第 4 轮，2026-09-08）

- 新增 `test_package/test_consumer.c`（应用外置规则文件场景，6 断言）：
  写 consumer_rules.clp（deftemplate+deffunction+defrule）→
  EnvBatchStar 缺失文件返回 0（负例）→ EnvBatchStar 加载规则文件 →
  assert 订单事实 → 文件加载的规则恰触发 1 次 → 文件加载的 deffunction
  计算 shipping-cost(3,10)=35
- 第 4 轮真机：**16/16 断言 PASS + CLI 端到端，CONAN_CREATE_RC=0**
- EnvBatchStar 语义（源码确认）：文件打不开返回 FALSE(0)；正常逐命令执行
  返回 TRUE(1)，单命令出错不改变返回值（下游断言兜底）

## W0 依赖检查

零外部依赖：纯 C，仅 libc + libm（链接 `-lm`）。`requirements()` 为空，
无制品仓依赖需要探测。sysdep.c 平台分支（LINUX）仅用 POSIX 标准头
（sys/types.h、sys/time.h、sys/times.h、unistd.h、signal.h），OHOS musl
sysroot 均提供。

## 源码与构建系统分析

zip 结构（清点证据，R51）：

```
$ unzip -l clips_core_source_630.zip | tail
    ... core/ 164 个 .c、163 个 .h
    ... makefiles/makefile.{gcc,g++,lib,lib++,win}
    ... readme.txt（许可证文本）
```

- **无 configure、无 CMake、无 Meson**：纯手工 Makefile（.c.o 后缀规则 +
  显式依赖表，gcc -MM 生成）。
- `makefile.gcc`：编译全部源（含 main.o）链接交互式 `clips`（-lm），
  编译器/命令硬编码 gcc。
- `makefile.lib`：编译除 main.c 外全部源为 `libclips.a`
  （`-DALLOW_ENVIRONMENT_GLOBALS=0`，`ar cq` 无 ranlib）。
  文件内注释给出库的官方用法：`gcc -o clips main.c -L. -lm -lclips`。
- makefile 需在 `core/` 目录内运行（源文件相对路径）。

### 平台适配点

- `setup.h` 平台宏（UNIX_V/LINUX/GENERIC...）默认全 0 → GENERIC 兜底
  （gentime 用 clock()，(operating-system) 返回 UNKNOWN）。
- 选 `-DLINUX`：sysdep.c 引入 POSIX 头、gentime 用 gettimeofday（或
  clock_gettime，需 _POSIX_C_SOURCE，默认不定义则走 gettimeofday，musl 下
  无条件声明）；(operating-system) 返回 LINUX。与 Debian 打包一致。
- 平台宏不影响推理引擎逻辑（全源码仅 sysdep.c/miscfun.c/engine.c 引用，
  均为信息性分支）。
- 交叉安全：构建过程只 编译 + ar + 链接，不执行任何构建期产物。
- 现代编译器兼容：C89 风格但无 K&R 缺陷；无 gets/mktemp/tempnam/sys_errlist
  等已移除 API（已 grep 清点）。

## 配方要点（conanfile.py）

- 静态库 + CLI 二进制：`libclips.a` → `lib/`，`clips` → `bin/`，
  `core/*.h` 全量平铺 → `include/`（clips.h 传递依赖整族头，带引号
  include 同目录查找）。
- shared=True 直接 `ConanInvalidConfiguration`（上游只有 ar 静态目标，
  不伪装支持）。
- R33：编译器路径取 `tools.build:compiler_executables` dict 的 "c"；
  AR/RANLIB 从编译器同目录推导 llvm-ar/llvm-ranlib（cdb 同款）。
- R9：make -j1。
- TMPDIR 注入 build 目录（真机 /tmp 只读，clang 需可写临时目录）。
- commands.json（软件级，type=tool）：bin/ 有 clips 可执行文件（PF8/R38）。

### 补丁

- `0001-makefile-lib-parameterize-toolchain.patch`（portability）：
  1. makefile.lib 头部新增 `CC ?= gcc` / `AR ?= ar` / `RANLIB ?= ranlib`；
  2. `.c.o` 规则 `gcc` → `$(CC)`，追加 `$(CFLAGS)`（空时行为与上游一致）；
  3. `libclips.a` 规则 `ar cq` → `$(AR) cq`，补 `$(RANLIB) $@`
     （上游无 ranlib 步骤，llvm-ar cq 产出的索引需 ranlib 保险）。

## 上游测试清点（R51 三步法）

1. **清点**：zip 内无任何测试目录/文件（仅 core/、makefiles/、readme.txt；
   164 .c + 5 makefile + 1 readme，`unzip -l` 全量核对）。CLIPS 官方测试
   载体是文档示例程序（clips_documentation_630.zip 独立分发）与 SourceForge
   bug 库，不随 core source 发布。→ `upstream_tests: []`。
2. **可运行环境实际运行**：上游无随包测试 → 无可运行项。
3. **test_package 实测回填**：自带 8 项断言（见 test_package/MANIFEST.yml），
   真机/shadow CI 运行后回填通过率。

## 本机验证记录（2026-09-08，Windows 主机）

- [x] 源码 URL + sha256 计算（downloads.sourceforge.net 官方源）
- [x] 构建系统识别（纯 Makefile；无 autotools/cmake/meson）
- [x] W0 依赖检查（零依赖）
- [x] 补丁 git apply --check 通过（对 pristine 解包源）
- [x] conanfile.py / test_package 语法检查（python compile + conan inspect）
- [x] 目录结构 L0a-L0e 自查（test_package/、conanfile.py、test.c、MANIFEST.yml 齐全）
- [ ] conan create：本机无 C 编译器且 validate 限定 Linux/OHOS → 留真机

## 真机构建与 test_package 首轮排障（2026-09-08）

真机直连 `ssh -T -p 2222 currentUser@10.62.134.118`，隔离作业范式
（独立 `clips-conan-home` + `clips-dl` 离线缓存 + `tools.build:jobs=1`），
与在跑的 botan3 -j1 任务并发，MemAvailable 全程 ~13GB。

- **构建零问题**：164 个 C 文件编译、libclips.a、clips CLI、打包全过；
  首次失败仅在 test_package 断言层（5/8 PASS）。
- **CLI 二进制真机验证通过**：`clips -f2 script.clp` 正常执行，
  defrule 触发、facts 输出正确、RC=0，无签名/弹窗阻塞。
- **排障结论（源码级证据）**：
  1. `EnvBuild` 每次调用只解析**一个** construct（strngfun.c：读 `(` →
     读类型名 → ParseConstruct 一次 → 返回，无循环）。拼接串
     `(a)(b)(c)` 只定义第一个 construct 即返回 TRUE——不是错误但易误用。
     修复：每个 construct 单独一次 EnvBuild。
  2. `EnvFunctionCall` 返回值遵循 CLIPS 错误约定：**TRUE(1)=出错，
     FALSE(0)=成功**（evaluatn.c FunctionCall2 返回 error 状态；函数
     不存在时也返回 TRUE 并打印错误）。嵌入式断言应写 `== 0` 并另验
     DATA_OBJECT 值。
  3. 对照实验：CLI 每行一条命令由 CommandLoop 逐条解析，故同逻辑在
     CLI 下正常——差异纯粹在 test.c 用法，不是库缺陷。
- 修复后断言 8 → 10 项（EnvBuild 拆分 + 语义修正）。

### 上游缺陷：DestroyEnvironment 对含 pending activation 的环境死循环

修复后二轮真机跑仍挂起（test_clips 6 分钟纯 CPU 空转，内存平稳）。
设备上以 -O0 调试程序 + timeout 做了 A/B/C/D 表征矩阵：

| 场景 | DestroyEnvironment | 结论 |
|---|---|---|
| A: fresh env 直接销毁 | 返回 1 正常 | teardown 机制本身可用 |
| B: 定义模板+规则（无事实匹配）后销毁 | 返回 1 正常 | 规则网络静态构建无碍 |
| C: reset+assert 产生 pending activation 后销毁（未 run） | **死循环** | 触发条件=agenda 非空 |
| D: run 触发规则后销毁 | **死循环** | 同上（run 后 agenda 仍留激活） |

- 定性：**上游 CLIPS 6.30 缺陷**（agenda/激活清理路径死循环），非适配问题、
  非 -DLINUX/OHOS 特有（纯引擎内部逻辑，无平台相关代码路径）。
- 影响：嵌入式 API 用户在 teardown 带 pending activation 的环境时挂起；
  随包 CLI 不受影响（main.c 注明控制流不从 CommandLoop 返回，从不销毁环境）。
- 处置：test_package 不对已用环境做 teardown（与 CLI 同款真实用法），
  另以 fresh env 验证 DestroyEnvironment API 正常；缺陷随 PR 说明。
  6.31/6.4x 是否修复未验证（任务口径锁定 6.3=6.30）。

### 鸿蒙特有测试（第 5 轮，2026-09-08，rule12 整改）

- 新增 `test_package/test_ohos.c`（2 用例 / 5 断言，覆盖 clips 与 OHOS 的两处真实交点）：
  1. **POSIX 时钟路径**：`(time)` 经 `-DLINUX` sysdep.c gentime 分支
     （clock_gettime/gettimeofday，musl）返回合理 epoch（> 1.7e9）——
     验证配方平台宏选择在 OHOS 上实际可用；
  2. **HMDFS 事实文件往返**：save-facts 写 TMPDIR（真机用户存储）、
     文件非空、fresh env load-facts 恢复、两条事实槽值正确。
- 待第 5 轮真机结果回填。
- **第 5 轮真机（2026-09-08）：test_ohos 5/5 PASS，总 21/21 断言 + CLI
  端到端，CONAN_CREATE_RC=0**（rule12 整改完成）。

## 下一步（真机 / shadow CI）

```sh
# 真机单包验证（不扫全仓）
CI_PACKAGES="archives/c/clips/6.3" zsh ci/conan/build_and_test.sh
# 或 shadow CI：
/path/to/run-ohos-shadow-ci.sh archives/c/clips/6.3
```

- 预计耗时：< 5 分钟（164 个 C 文件单线程编译，小库）
- 资源类型：CPU 短时
- 关注点：make 在 core/ 内的后缀规则是否被 OHOS make 完整支持；
  `clips -f2` 的 stdin EOF 退出行为；grep 断言输出。

## 已知限制

- 仅静态库（上游无共享库支持）。
- 版本号 6.3 vs 上游文件 6.30：PR 描述中说明映射关系。
- (system) 函数（gensystem）依赖系统 shell，OHOS 环境下未验证；
  不影响推理核心。
