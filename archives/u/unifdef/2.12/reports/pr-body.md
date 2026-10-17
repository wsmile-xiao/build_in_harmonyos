- **三方库名称**：unifdef（选择性移除 C 预处理器条件编译 `#if`/`#ifdef`/`#ifndef` 的命令行工具）
- **上游版本**：2.12
- **上游仓库地址**：https://dotat.at/prog/unifdef/（发布源 `https://dotat.at/prog/unifdef/unifdef-2.12.tar.gz`，官方 HTTPS 源）
- **适配路径**：路径 A（基础适配，零补丁）
- **使用知识库**：无正式条目命中（零补丁、零依赖、无构建错误，未触发知识图谱匹配）；适配知识已沉淀于版本级 `manifest.yaml` 的 `knowledge_gained`（5 条）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试/回归 | 90 | 来源：`tests/*.sh`（`make test` → `scripts/runtests.sh`，逐例比较 `.out/.err/.rc` 与 `.expout/.experr/.exprc`） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **90** | 上游 tarball 自带完整回归套件 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游回归（全量保留执行） | 90 | 不变（未改一例） | OHOS 设备实测 82 通过；8 例为宿主环境不兼容（逐项原因见下），与 unifdef 本体无关 |
| 鸿蒙特有测试（消费者视角） | 12 | **新增** | `test_package/test_unifdef.sh` 真实执行已安装的 `unifdef`/`unifdefall`，12/12 通过 |
| **合计** | **102** | **+12** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：90 例上游测试**零修改**。`conanfile.py` 的 `build()` 全量执行 `make test`，
> 失败集合取 `tests/*.rc` 残留与日志 `FAILED:` 行的并集，并强制"进度标记数 ≥ 用例数"
> 下限；仅对下列 8 例宿主环境不兼容用例做显式白名单容忍，**白名单外任何失败立即
> raise 中止构建**（fail-closed）。8 例原因逐项登记于 `test_package/MANIFEST.yml`、
> `manifest.yaml`（knowledge_gained）与 `reports/test-report.md`：
> 1. `if1-a`、`if2-a`、`if3-a`、`if4-a`、`if5-a`：`unifdefall` 调用宿主 `cc -E -dM`
>    预处理 `.c` 文件；OHOS SDK 交叉 clang 无默认 sysroot，`#include <stdio.h>` 报
>    `fatal error: 'stdio.h' file not found`。unifdef 本体在该用例中已先行成功执行。
> 2. `multimissing`、`multinewline`：期望输出内嵌 GNU diff -u 的 hunk 头/报错文案；
>    OHOS 自带 toybox diff 为不同方言（被比较的内容行一致，仅 hunk 范围/错误文案不同）。
> 3. `outeperm`：HMDFS 不强制 `chmod(2)` 只读目录语义（0555 目录仍可写），无法复现
>    期望的 `Permission denied` 与 rc=2。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（90 例 shell 回归全量执行）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 适配新增了消费者视角的 `test_package`（12 条断言），用于验证**安装后的产物**：
> `-V`/`-h` 输出、`-D`/`-U` 分支选择、退出码语义（0=未变化 / 1=有变化）、`-s` 符号列举、
> 嵌套条件、`-m` 原地修改、`-M~` 备份、`unifdefall` 可执行性。该项不属于对"上游无测试"
> 的补全（上游测试完整），CI L1e 破坏性反向验证已确认该测试真实依赖被测包。

## 验证结果

- 编译状态：**通过**（`conan-verify` G0–G4 与 L2/L4/L5 全 PASS；`finish` W3 本地 CI 阻塞门禁 PASS，`conan create` EXIT=0；profile `ohos-aarch64-device`）
- 上游测试用例通过率：**82/90（91.1%）**；未通过的 8 例均为宿主环境不兼容（逐项原因见上），与 unifdef 本体相关的全部用例 100% 通过
- 新增测试用例通过率：**12/12（100%）**
- 本地 CI 等价门禁：G0/KC/JC/L0/L1/L1e/L4/L5 PASS；L2 smoke 为非阻塞 skip（unifdef 上游 CLI 不支持 `--version`/`--help`，仅支持 `-V`（rc=0）/`-h`（rc=0，打印 usage），后者已由 test_package 实测覆盖）

## 补充说明

### 适配要点

1. **零补丁**：上游为单文件 ANSI C + POSIX Makefile，不经修改即可用 OHOS SDK clang（aarch64-linux-ohos）构建，`patches/` 为空，无平台宏（R8）。
2. **零依赖**：`requires` 为空（W0 检查：无第三方库，仅链接系统 libc）。
3. **编译器来源**：`build()` 从 Conan conf `tools.build:compiler_executables.c` 取 clang 路径（R33），`make -j1`（R9）。
4. **package() 直接 copy 产物**：上游 `make install` 依赖 `install(1)` 并在 man 目录创建软链接，CI worker PATH 无保证；改为直接 copy `bin/unifdef`、`bin/unifdefall` 与 man 手册（`unifdefall.1` 以 unifdef.1 副本提供）。
5. **CLI 声明**：软件级 `commands.json`（R38，`type=tool`，`ref=unifdef/2.12`）。
6. **退出码语义**：0=输出与输入一致 / 1=输出有变化 / 2=错误；test_package 覆盖 0/1 两条路径。

### 已知限制

| 项 | 技术原因 |
|----|----------|
| `unifdefall` 的预处理步骤 | 依赖宿主可用的 C 预处理器（`cc -E`）与 `sort`/`sed`；在无 sysroot 的交叉工具链环境下不可用。主程序 `unifdef` 不受影响。 |
| 8 例上游用例 | 宿主环境差异（宿主 cpp/无 GNU diff/HMDFS chmod 语义）。在具备对应能力的环境可自然转绿；白名单机制不影响结果真实性（全量运行 + 如实登记）。 |

### 验证证据

| 证据 | 位置 |
|------|------|
| 上游 82/90 + test_package 12/12 明细 | `2.12/reports/test-report.md` |
| 本地 CI 全门禁日志（含 conan create） | `2.12/reports/w3-local-ci.log` |
| W4 独立审计（verdict=pass，0 P0/P1；2 个 P3 为承前开放项） | `2.12/reports/audit-result.json` |
| conan-verify 报告（G0–G4/L2/L4/L5 PASS） | `2.12/reports/conan-verify-report.md` |
| 适配笔记（含 7 项问题与解决方案、逐项环境差异说明） | `2.12/notes.md` |
