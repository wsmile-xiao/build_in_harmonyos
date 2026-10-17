- **三方库名称**：lrcalc
- **上游版本**：1.2
- **上游仓库地址**：https://sites.math.rutgers.edu/~asbuch/lrcalc/ （源码仓库 https://bitbucket.org/asbuch/lrcalc ）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：是（E007 config.guess/config.sub 三元组补丁；E011/E129 HMDFS umask 077 临时目录不可写；E386 HMDFS 下 shell 能力不稳）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无独立单元测试框架 |
| 集成测试 | 8 | 来源：`Makefile.am` 的 `TESTS = testsuite`，端到端运行 `lrcalc`/`schubmult` 并逐字节比对输出 |
| 其他测试 | 0 | |
| **合计** | **8** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 8 | 不变 | 上游 `testsuite` 原样运行（`make check`） |
| 鸿蒙特有测试 | 7 | 新增 | `test_package/`：C 消费者 3 项 API 断言 + CLI 消费者 4 项输出比对 |
| **合计** | **15** | **+7** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（`testsuite`，8 项检查，原样通过）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 另按仓库规范补全了 Conan `test_package/`（CI 自动执行，消费者视角）：
> - `test.c`：通过 Conan 生成的 CMake 配置链接 `liblrcalc`，调用导出 API（`v_new_init`/`lrcoef`）断言 3 个 Littlewood-Richardson 系数（2 / 1 / 0）
> - `test_lrcalc.sh`：运行打包的 `lrcalc`、`schubmult` 可执行文件，与上游 README 示例逐字节比对（coef/skew/mult -q/schubmult 共 4 项）

## 验证结果

- 编译状态：通过（`conan create` 全流程成功；conan-verify G0–G4 全部 PASS）
- 上游测试用例通过率：8/8（100%）
- 新增测试用例通过率：7/7（100%）（C 消费者 ctest 1/1、CLI 4/4、CI L1e 破坏性反向验证通过）
- 本地 CI 门禁（`ci/conan/build_and_test.sh`，与平台 CI 同脚本）：L0 pass / L1 pass / L1e pass / L5 pass；L2 skip（lrcalc 不提供 --version/--help，非阻塞）、L4 warn（补丁文本正则 `gets` 误命中 config.guess 中 "targets"，已知非阻塞）
- W4 独立审计：verdict=pass，P0=0 / P1=0（`reports/audit-result.json`）

## 补充说明

- 上游构建系统为 autotools（tarball 自带 2014 年生成的 `configure`），无任何外部依赖（仅 libc），产物包含 `liblrcalc.so`、`lrcalc`、`schubmult` 与全部头文件。含可执行文件，已按 R38 在软件级目录声明 `commands.json`。
- 适配补丁（均已在 conandata.yml 声明，不含平台宏）：
  1. `0001-config.guess.patch`：识别 `uname -s=HarmonyOS`，输出 `aarch64-unknown-linux-ohos`——native 构建时 conan 不传 `--host/--build` 三元组，configure 必然运行 config.guess（E007）；
  2. `0002-config.sub.patch`：接受 `linux-ohos*` OS token（E007 同族，POSIX 修复）；
  3. `0003-configure.patch`：临时目录 `umask 077` → `022`，规避 HMDFS setgid 目录不可写导致 `config.status` 在 `subs1.awk` 处失败（E011/E129）。
- 配方内额外处理：profile 注入的 harmonybrew bash 作为 SHELL 会破坏 libtool/config.status（E386 同族），configure 命令行强制 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`；`make -j1` 规避 HMDFS 对 jobserver FIFO 的限制；CI profile 未提供 `tools.build:compiler_executables` 时回退 `CC=clang`/`CXX=clang++`（tslib/adplay 先例）。
- 已知非阻塞项：`share/lrcalc/lrcalc.maple` 中记录构建期 prefix 路径（Maple 接口脚本内部路径，不影响库与命令行行为）；上游未提供 `--version/--help`（L2 skip）。
