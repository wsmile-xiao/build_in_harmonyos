- **三方库名称**：lutok
- **上游版本**：0.6.2
- **上游仓库地址**：https://github.com/jmmv/lutok
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，见下方"路径 B 知识贡献说明"）
- **使用知识库**：E007/E160（config.guess 识别 HarmonyOS）、E011/E129（HMDFS mktemp -d 与 config.status 临时目录）、E522（transitive .la / dependency_libs 不可迁移，引用）、E480（公开头依赖须 transitive_headers，引用）；本 PR 按路径 B 新增知识草稿 `E580-draft-9C4A`（ATF/kyua 测试栈无 kyua 全量执行协议）
- **任务号**：8609
- **分支**：feat/lutok-0.6.2

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 97 | 来源：6 个 atf-c++ 测试程序（c_gate 2 / debug 2 / exceptions 4 / operations 19 / stack_cleaner 4 / state 66，按源码 `ATF_ADD_TEST_CASE` 清点） |
| 集成测试 | 4 | 来源：`examples_test`（atf-sh，编译并运行 bindings/hello/interpreter/raii 四个上游示例） |
| 其他测试 | 0 | 上游无其他自动化测试；`Kyuafile` 由 kyua 编排（kyua 未适配 OHOS） |
| **合计** | **101** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 97 | 不变 | 真机全量执行（`prog -l` 枚举 + 逐用例运行），97/97 通过 |
| 集成测试 | 4 | 不变 | `examples_test` 在 `make install` 后真实编译并运行 4 个示例，4/4 通过 |
| 鸿蒙特有测试（消费者） | 1 | **新增** | `test_package` 消费者程序 `test_lutok`：do_string 求值、native 模块调用、stack_cleaner、失败脚本抛 `lutok::error`、`state_c_gate` 裸 `lua_State`，共 6 处断言；另验证包内 `lua.hpp` 包装头可用 |
| **合计** | **102** | **+1** | 上游 101 用例全保留执行 + 新增消费者测试 1 |

> 执行口径：kyua 未适配 OHOS，上游 ATF 程序以自身 CLI 全量执行——`prog -l` 枚举（TP 格式 `ident:`）+ `prog <case>` 单用例运行（退出码 0=通过）；配方内按"每程序用例数 + 总数/通过数"强对账，防少跑或静默跳过（详见 `reports/atf-cxx-upstream-tests.log`、`reports/examples-upstream-tests.log`）。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：本适配**零补丁**，上游源码与测试文件保持原样（连构建脚本也未修改）；所有平台差异通过 conanfile 生成阶段与运行环境注入完成。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（101 个上游用例全量真实执行）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 消费者测试（`test_package`）为赛道要求的消费者视角验证，不替代上游测试统计。

## 验证结果

- 编译状态：通过（`conan create` 全量验证 EXIT=0，profile `ohos-aarch64-device`，含上游套件执行 + test_package）
- 上游测试用例通过率：**101/101（100%）**（97 atf-c++ + 4 atf-sh 示例，逐用例计数见 `reports/test-report.md`）
- 新增测试用例通过率：**1/1（100%；6 处断言）**

## 路径 B 知识贡献说明

- **新增草稿**（与归档适配同一原子 PR 交付）：
  - `knowledge/drafts/E580-draft-9C4A.kv` / `.md`
  - 拟提升编号 E580（以知识库主编 promote 为准）；`draft-review` 预审建议 **create（疑似新知）**
- **知识主题——ATF/kyua 测试栈在 OHOS 无 kyua 时的全量执行协议**：
  1. **无 kyua 全量执行协议**：ATF 测试程序只有 `-l`（枚举，TP 格式 `ident:`）与单个位置参数（运行一个用例，退出码判定）两种能力；`-r` 是**结果文件参数**而非"运行全部"（预研文档误读，本轮以 ATF 0.23 源码 `atf-c++/tests.cpp` getopt `:lr:s:v:` + 实测纠正）；以"每程序用例数 + 总数/通过数"强对账防少跑；
  2. **atf-sh 装配**：脚本 shebang 取自 `pkg-config --variable=interpreter atf-sh`，atf-sh 编译期默认 `ATF_SHELL`/`ATF_LIBEXECDIR`/`ATF_PKGDATADIR` 可能是构建机私有路径（本实例为 CI-worker 的 `/data/service/hnp/bin/bash`），运行前必须显式覆盖；
  3. **examples_test 的安装期依赖**：示例套件用 `make`+`pkg-config` 编译链接到**已安装**的库，必须在 `make install` 之后运行；
  4. **衔接**：kyua 适配落地后可无缝切回 `kyua test -k Kyuafile` 编排，用例集合不变。
- **触发实例**：lutok 0.6.2 真机适配（本 PR）。三类失败均有原始日志与逐层定位记录（`notes.md`）：`Must provide a test case name`、`Failed to execute /data/service/hnp/bin/bash`、示例套件安装期依赖。
- **查重结论与新增价值**（`draft-review` 预审，index.tsv **766 条** + drafts **859 个文件**，2026-09-17 实查）：
  - `atf`/`kyua`/`atf-sh`/`libatf`/`ATF_` 在正式条目与草稿中 **0 命中**（word-boundary 实查）——空白区；
  - 预审质量：signature/root_cause/rec 全 ✅；TOP5 相似度 E165=0.20（仅 atf-sh 私有 shell 路径字符串重合）、E066=0.17、E526=0.15、E239=0.12、E049=0.12 → **建议 create**；
  - **边界（草稿 md 中逐条划界，不重复申报）**：E272（DejaGNU spawn/tmpfile 单点）、`DRAFT-dejagnu-toolchain-assembly-ohos`（DejaGNU 工具链装配）、`DRAFT-bats-suite-ohos-runtime-shims`（bats 运行时 shim）、`DRAFT-nut-autotools-ohos-upstream-check-chain`（通用 autotools check 环境）、E228（libtool wrapper 执行位）、E011/E129（mktemp）、E522/`DRAFT-ccfits-2.7-stale-pc-prefix-regen`（.pc/.la 不可迁移，仅引用）、E480/`DRAFT-conan-shared-pkgconfig-requires-drop`（transitive_headers，仅引用）。
- **验证证据**：`reports/test-report.md`、`reports/atf-cxx-upstream-tests.log`（97 PASS）、`reports/examples-upstream-tests.log`（4 PASS）、`reports/w3-local-ci.log`、`reports/audit-result.json`（W4 独立审计 pass，0 P0/P1）。
- **知识库扩展 Issue**：[#3071](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3071)（与本 PR 双向关联）。

## 补充说明

### 构建系统与关键适配点

lutok 0.6.2 使用 **GNU Autotools**（官方 release 附件为 `make dist` 产物，自带 `configure`）：

1. **零补丁**：上游源码未做任何修改；`config.guess` 不识别 HarmonyOS 通过显式
   `--build/--host=aarch64-unknown-linux-gnu` 绕过（E007/E160）；
2. **HMDFS 临时目录**：toybox `mktemp -d`（umask 077）建出的目录不可写，config.status 报
   `could not setup config files machinery`；配方以 mkdir 版 `mktemp` shim 前置 PATH（E011/E129）；
3. **Lua 发现**：`PkgConfigDeps` 依据 lua/5.4.8 的 `pkg_config_name=lua-5.4` 生成 `.pc`，
   `m4/lua.m4` 第一级探测命中；lua 制品缺 `lua.hpp`，配方生成标准四行包装头用于构建并随包安装；
4. **C++20**：上游 `AX_CXX_COMPILE_STDCXX(20,...)` 强制 C++20，而 profile `cppstd=17` 的
   `-std=c++17` 位置更靠后，配方在 `extra_cxxflags` 末尾追加 `-std=c++20` 保证生效；
5. **atf 制品消费边界**：atf/0.23 的 `.pc`/`.la` 为 `prefix=/` 构建产物、编译期 `ATF_SHELL`
   为构建机私有路径；配方自写包装 `.pc` + `.a` 私有 link 目录绕开坏 `.la` + 运行期 `ATF_*` 覆盖；
6. **公开头依赖透传**：c_gate.hpp 暴露 Lua C API，lua 以
   `transitive_headers=True, transitive_libs=True` 声明，避免 Conan 图将 lua 在消费者图标 Skip（E480）。

### 验证命令

```bash
python3 scripts/ohc-run.py conan-verify lutok 0.6.2 --profile ohos-aarch64-device
python3 scripts/ohc-run.py finish lutok 0.6.2 built
# 上游套件（配方 build() 内自动执行，逐用例 + 强对账）：
#   atf-cxx: SUMMARY total=97 passed=97 failed=0
#   examples: SUMMARY total=4 passed=4 failed=0
# 消费者：test_lutok: 6 checks passed
```

### 已知限制

| 未执行项 | 技术原因 |
|----------|----------|
| `make check`（kyua 编排） | kyua 未适配 OHOS（后续任务 #7994）；本 PR 以 ATF 程序 CLI 全量执行 101 用例，用例集合与 Kyuafile 注册一致，无跳过项 |

### 本次知识路径说明

按仓库先例（#9734 cdo / #9735 cln / #9810 cyrus-sasl-sql）在同一 PR 内原子交付知识草稿与
「路径 B 知识贡献说明」，PR 标题使用【知识库扩展】前缀；未新开 PR、未换分支、未改动任何框架文件
（`ci/`/`scripts/`/`templates/`/`SKILL.md` 等）。新增知识与本适配过程一一对应，证据可从
`notes.md` 与 `reports/` 复现。
