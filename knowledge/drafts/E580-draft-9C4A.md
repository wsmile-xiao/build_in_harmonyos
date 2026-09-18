# E580（草稿）：ATF/kyua 测试栈在 OHOS 无 kyua 时的全量执行协议

- **草稿 ID**: E580-draft-9C4A（编号以主编 promote 时为准）
- **触发实例**: lutok 0.6.2 适配（任务 #8609，分支 feat/lutok-0.6.2，2026-09-17）
- **类别**: testing / autotools / conan / ohos
- **证据强度**: ★★★★★（101 个上游用例逐条真实执行日志 + 用例数强校验 + 消费者测试）

## 症状（可复现）

ATF（atf-c++ / atf-sh）编写的上游测试套件在 OHOS 上**没有 kyua 可用**（kyua 属后续适配任务）：

```text
# 上游 Kyuafile 注册 7 个测试程序，但 kyua 不存在：
$ kyua test -k Kyuafile
kyua: inaccessible or not found

# 直接裸执行测试程序只得到警告，且一次只能跑一个用例：
$ ./c_gate_test
c_gate_test: WARNING: Running test cases outside of kyua(1) is unsupported
c_gate_test: WARNING: No isolation nor timeout control is being applied; ...
c_gate_test: ERROR: Must provide a test case name
c_gate_test: See atf-test-program(1) for usage details.

# atf-sh 套件（examples_test）在制品环境里可能直接无法启动：
Failed to execute /data/service/hnp/bin/bash: No such file or directory
```

## 根因

1. **kyua 编排缺失**：ATF 程序本身**没有"运行全部用例"的选项**。atf-c++/atf-sh 测试程序的 CLI 是
   `-l`（列出用例，TP 格式 `ident:`）、`-r <file>`（**结果文件路径**，不是运行全部）、`-s`（srcdir）、
   `-v`（变量）与**一个位置参数**（单个用例名，退出码 0=通过）。上游靠 Kyuafile+kyua 完成
   "枚举→逐个运行→汇总"；kyua 缺席时没有现成范式，容易被误当成"测试无法运行"。
   （预研文档曾把 `-r` 误判为"运行全部用例"；ATF 0.23 源码 `atf-c++/tests.cpp` getopt `:lr:s:v:` 与实测均证伪。）
2. **atf-sh 自举环境不可迁移**：atf-sh 脚本的 shebang 来自
   `pkg-config --variable=interpreter atf-sh`（`.pc` 的 `interpreter=${exec_prefix}/bin/atf-sh`）；
   atf-sh 二进制的编译期默认值 `ATF_SHELL` / `ATF_LIBEXECDIR` / `ATF_PKGDATADIR` 可能是**构建机私有路径**
   （本实例为 CI worker 的 `/data/service/hnp/bin/bash`），消费者运行前必须显式覆盖。
3. **examples_test 的安装期依赖**：atf-sh 示例套件用 `make`+`pkg-config` 把上游示例编译链接到
   **已安装**的库（`ExamplesDir`/`LibDir` 为 configure 时的 `$(docdir)/examples`、`$(libdir)`），
   因此必须在 `make install` **之后**运行，不能用源码树里未安装的产物替代。

## 方案（可跨库复用）

**A. 无 kyua 全量执行协议（推荐）**

```sh
# 1. 枚举：-l 输出 TP 格式，逐行取 ident
cases=$(./prog -l | sed -n 's/^ident: //p')
# 2. 逐用例执行：单个位置参数；退出码 0=通过，非 0=失败
for tc in $cases; do ./prog "$tc" || echo "FAIL $tc"; done
# 3. 对账：各程序用例数须与源码清点（ATF_ADD_TEST_CASE 计数/上游清单）一致，
#    总数、通过数、失败数须与日志逐条一致（防少跑/静默跳过）
```

要点：裸执行打印的 kyua 警告不阻断、不影响退出码语义；用例计数必须以**源码清点**为基准做强校验。

**B. atf-sh 套件的运行环境**

```sh
export ATF_SHELL=<设备真实 shell 绝对路径>          # 覆盖编译期私有默认值
export ATF_LIBEXECDIR=<atf 包>/libexec             # atf-check
export ATF_PKGDATADIR=<atf 包>/share/atf           # libatf-sh.subr
# examples_test 必须在 make install 之后运行；PKG_CONFIG_PATH 指向安装前缀的 .pc
```

**C. 过渡与衔接**：kyua 适配落地后直接
`kyua test -k Kyuafile --build-root=<builddir>` 编排；用例集合与逐用例执行完全一致，可无缝切换，
本范式即"运行器缺席期的可证执行"。

## 真实验证

- lutok 0.6.2（任务 #8609）：6 个 atf-c++ 程序 **97/97**（c_gate 2 / debug 2 / exceptions 4 /
  operations 19 / stack_cleaner 4 / state 66）+ atf-sh `examples_test` **4/4**（bindings/hello/
  interpreter/raii 真实编译执行），合计 **101/101**；日志见归档
  `archives/l/lutok/0.6.2/reports/{atf-cxx,examples}-upstream-tests.log`；
- 配方内以 `-l` 枚举数量与预期逐程序比对、`SUMMARY total/passed/failed` 不符即抛错（用例数强对账）；
- 消费者测试同时验证 `<lutok/c_gate.hpp>` 可用（生成缺失的 `lua.hpp` 包装头）。

## 与现有知识库的关系（查重，2026-09-17：index 766 + drafts 859）

| 既有条目/草稿 | 内容 | 本条增量 |
|---|---|---|
| **E272**（DejaGNU） | `expect spawn`/`-nottyinit`、`tmpfile` shim 两个单点 | **不重复**。本条是 ATF 框架的**协议层**执行范式（TP 枚举、单用例位置参数、atf-sh 自举环境、用例对账）；框架族不同 |
| **DRAFT-dejagnu-toolchain-assembly-ohos**（dwz 48/62） | DejaGNU 工具链装配（tcl/expect 版本链等） | 不重复，框架族不同且解决的问题面不同 |
| **DRAFT-bats-suite-ohos-runtime-shims**（bork 366/366） | bats 运行时 shim | 不重复，bats 无"编排器缺席"问题（自带 runner）；本条核心是 kyua 缺席时的协议级执行 |
| **DRAFT-nut-autotools-ohos-upstream-check-chain** | autotools `make check` 环境闭合（gawk/PATH/LN_S） | 不重复，本条不涉及通用 autotools 环境，只涉及 ATF 程序 CLI 与 atf-sh 环境 |
| **E228**（Libtool wrapper） | `.libs`/`LOG_COMPILER`/执行位 | 不重复；ATF 程序在 libtool wrapper 下正常执行，仅引用 |
| **E143/E165**（shebang/解释器路径） | 系统无传统 /bin，bash 位于 /data/service/hnp/bin/bash 等 | 不重复：E165 处理"解释器路径迁移"本身；本条处理 atf-sh **自举环境的运行期覆盖**（ATF_SHELL/ATF_LIBEXECDIR/ATF_PKGDATADIR 三个专用变量），且只是四部分协议中的一环 |
| **E011/E129**（mktemp/config.status） | HMDFS 临时目录 | 已被覆盖，仅引用 |
| **DRAFT-ccfits-2.7-stale-pc-prefix-regen / E522** | 依赖包 `.pc` 陈旧 prefix、`.la` 不可迁移 | 已被覆盖；本条仅把它们列为"消费 atf 制品时的边界"，不重复申报 |
| **E480 / DRAFT-conan-shared-pkgconfig-requires-drop / DRAFT-ohos-public-header-transitive-dep** | `transitive_headers`/`skip_binaries` | 已被覆盖，不重复申报（本适配按既有知识处置） |

`draft-review` 预审（2026-09-17，index 766 条）：质量预检 signature/root_cause/rec 全 ✅；TOP5 相似度 E165=0.20（仅 atf-sh 私有 shell 路径字符串重合）、E066=0.17、E526=0.15、E239=0.12、E049=0.12；**预审建议 create（疑似新知）**。候选正式条目编号由主编 promote 时分配。

## 附属小节（关联现象，不单独成条）：依赖制品缺失 C++ 便利头（lua.hpp）

同任务实测（lutok 依赖 lua/5.4.8）：lua 制品只安装 `*.h` 与 `liblua.a`，缺上游发行版自带的
C++ 便利头 `lua.hpp`，而依赖方公开头可能直接包含它（本实例 `c_gate.hpp`），消费者编译报
`fatal error: 'lua.hpp' file not found`。处置：在私有 build prefix 生成标准四行包装头
（`extern "C"` 包 `lua.h/lualib.h/lauxlib.h`），构建期经 `-I` 使用并随包安装到 `include/`，
消费者无需额外处理；同时 Lua 的多命名 pkg-config 探测链（`lua-5.4`/`lua5.4`/`lua`）在制品仓首次命中。
边界：属"依赖制品完整性"的实例，与 E480 / `DRAFT-ccfits-2.7-stale-pc-prefix-regen` 等同族，
故不单独申报，仅作为本条的关联支撑事实。

## 适用范围与边界

- **适用**：ATF（atf-c++/atf-sh）或 kyua 编排的测试栈在**运行器缺席**平台的适配与执行；
  同样适用于"任何测试框架编排器不可用、但测试程序可独立运行"的过渡执行与对账。
- **边界**：不解决 kyua 本体适配（任务 #7994）；不替代 test_package（消费者层验证）；
  不适用于完全不支持独立运行的框架（如必须由 runner 注入环境的场景）。
- **解除条件**：kyua 适配完成并发布后，可切回 `kyua test -k Kyuafile` 编排（本范式保留为离线/最小环境执行手段）。
