# odinfmt dev-2026-06 适配笔记（HarmonyOS PC · aarch64）

## 定位
- Odin 语言官方代码格式化工具，产出 `bin/odinfmt` 单一可执行文件。
- 登记版本 `dev-2026-06` = 上游 `DanielGavin/ols` tag `dev-2026-06`
  （commit `fa36fac9770c1715c33c13755bd4090b1959159f`）。
- 上游无独立仓：`odinfmt` 源码在 `ols` 仓的 `tools/odinfmt/`，格式化核心在
  `ols` 的 `src/odin/format` + `src/odin/printer`，故 source 取 ols 源码树
  （2026 年起 Odin 主仓 `tools/` 已移除，github API 证实 404）。

## 上游构建系统剖析
- `ci.sh` 的构建步骤（CI 环境）：
  `odin build tools/odinfmt/main.odin -file -show-timings -collection:src=src -out:odinfmt -no-bounds-check -o:speed`
- `odinfmt.sh`（开发者本地）：同命令去掉 `-no-bounds-check`。
- 上游测试（`ci.sh CI` → `tools/odinfmt/tests.sh`）：
  `cd tools/odinfmt && odin run tests.odin -file -collection:src=../../src -out:tests.exe`
- 纯 Odin 工具链驱动，无 CMake/Make/configure，无平台分支。

## 关键适配（相对上游）
1. **无补丁**：本平台对上游源码零修改。`odin` 编译器产物在本平台可直接运行，
   构建命令、`-collection:src` 相对路径语义均与上游一致。0 补丁，0 上游文件改动。
2. **依赖链**：`odinfmt` ← `odin` 编译器 ← `llvm/22.1.0`（odin 运行期 LLVM）。
   两者均以 `tool_requires` 引入（构建期工具），不进入 `odinfmt` 包的运行期依赖。
   - odin 编译器取自本地/制品仓 `odin/dev-2026-08`（同批 odin 适配已双绿）。
   - `llvm/22.1.0` 供 odin 运行期解析 `libLLVM.so.22.1`。
3. **env 注入方式（与 odin 配方的差异，已实测确认）**：odin 的 llvm 是 host
   `requires`，所以 `env="conanrun"` 即可拿到 `lib/`；odinfmt 的 odin 是
   build context 工具，其运行环境由 conan 聚合进 `conanbuild`（VirtualBuildEnv），
   `conanrun` 不覆盖。为避免依赖 conan env 脚本的语义细节，配方直接用
   `self.dependencies.build[...].package_folder` 构造：
   `ODIN_ROOT=<odin 包根>`、`LD_LIBRARY_PATH=<llvm 包根>/lib:$LD_LIBRARY_PATH`
   —— 路径仍来自 conan 依赖图，无硬编码制品仓路径。
   - 缺 `LD_LIBRARY_PATH` 时的真实报错：`Error loading shared library
     libLLVM.so.22.1 (needed by ./odin)` + 连锁符号重定位失败（rc=127）。
4. **签名**：`bin/odinfmt` 为 ELF 可执行文件，OHOS XPM 要求 binary-sign-tool
   自签（llvm-objcopy 去 `.codesign` 后重签），build 与 package 各一次。

## 产物形态
- `bin/odinfmt`（858 KB，动态 ELF）：`DT_NEEDED` 仅 `libc.so`，`RUNPATH=$ORIGIN`
  → 运行期无第三方动态库依赖，消费者不需要任何环境变量。
- 包内另含上游 `LICENSE`（MIT）。

## 测试设计
### 上游测试（构建期真跑，非致命记录）
- `tools/odinfmt/tests.odin`：快照（golden file）测试，遍历 `tests/` 下输入 `.odin`，
  格式化后与 `.snapshots/` 同名快照逐字符比对。共 **22 例**，无网络、无外部资产。
- 本机实跑结果：**21 例通过 / 1 例不一致 / 1 例被短路未执行**（单独复跑通过）。
  - 不一致例：`tests/random/demo.odin`。差异为 **10 处行注释的尾随空白**
    （dev-2026-06 快照保留、本适配剥离），无非空白字符差异。
  - 归因（已实证）：本适配对 `demo.odin` 的输出与上游 **ols dev-2026-08** 的
    `.snapshots/demo.odin` **逐字节一致**（`cmp` 通过）。ols 的 format/printer
    依赖 Odin 自带 `core:odin/parser` 与 `core:odin/tokenizer`，跨 Odin dev 版本
    存在注释尾随空白行为差异；本仓 odin 编译器为 dev-2026-08，故 dev-2026-06 的
    该快照相对本工具链已陈旧，非 HarmonyOS 平台适配缺陷。
  - 未修改上游任何测试用例与快照（PR 字段如实勾选"否"）。

### test_package（消费者视角，5 项）
1. 无参数调用 → 输出 Usage 且 exit≠0、stderr 含 `Missing path to format`（CLI 契约）。
   （注：odinfmt 无 `--version`/`-help` 开关，`--help` 报
   `Unable to find any flag named '-help'`，故 CLI 断言改为无参数用例。）
2. 文件模式：`odinfmt -config:odinfmt.json sample.odin` 的 stdout 与 `expected.odin`
   逐字节一致（`diff -u`）。
3. 幂等性：对 `expected.odin` 再格式化，结果不变。
4. `-stdin` 模式：输出与文件模式一致。
5. `-w` 写回模式：目标文件内容变为 `expected.odin` 内容，且不残留 `*_bk` 备份。
- `sample.odin` 为故意误排版的输入；`expected.odin` 为规范化输出（同时是幂等测试的期望）。
- 测试显式传 `-config`：`odinfmt` 不指定配置时 `find_config_file_or_default`
  会向上逐级查找 `odinfmt.json`，可能命中源码树根配置导致输出变化，显式传参保证确定性。

## 验证命令
```bash
conan create archives/o/odinfmt/dev-2026-06 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
# CI 等价（强制重建）：-pr:h=... -pr:b=... --build=odinfmt/*
# 结果：rc=0；build() 内上游快照测试真跑并记录
#       "[rule4] upstream-tests odinfmt-snapshot attempted=21 passed=20 failed=1"；
#       test_package 5/5 通过
```

## 已知限制
- 上游快照测试 1 例（`tests/random/demo.odin`）因上游快照相对 Odin dev-2026-08
  工具链陈旧而不一致（仅尾随空白），未修改上游快照；归因见上。
- 依赖 `odin/dev-2026-08` 需先在制品仓发布（R36：依赖必须先发布），否则 CI 的
  L0i 依赖发布检查会拦下本包。
