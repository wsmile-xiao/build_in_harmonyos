# application 包的可用性不能靠 `--version` 断言

> Draft: `DRAFT-ZPAQ-715-NO-VERSION-FLAG-SMOKE-GATE`
> Stem: `zpaq-7.15-no-version-flag-smoke-gate` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-ZPAQ-715-NO-VERSION-FLAG-SMOKE-GATE
- **严重度**: 3
- **类别**: testing|ci-gate|packaging
- **触发工具**: conan|ci
- **阶段**: testing

## 错误特征

门禁侧（`conan-verify` L2、CI L2 冒烟）报：

```
⚠️ bin/zpaq: --version 和 --help 均失败
```

而被测工具本身完全正常。实测 zpaq 7.15：

```
$ ./zpaq --version ; echo "exit=$?"
zpaq v7.15 journaling archiver, compiled Sep 25 2026
Unknown option ignored: --version
Usage: zpaq command archive[.zpaq] files... -options...
exit=1

$ ./zpaq --help   -> 同样打印用法，exit=1
$ ./zpaq -v       -> 同上
$ ./zpaq          -> 同上
```

即：**任何**未识别参数都打印横幅 + 用法并 `exit 1`。

但"错误一律返回 0"的说法**不成立**——逐条实测的退出码是三值的：

| 调用 | 退出码 | 输出 |
|------|--------|------|
| 无参数 / 未知选项（含 `--version`） | 1 | 横幅 + 用法 |
| `x <不存在的归档>` | **2** | `<archive>: No such file or directory`（stderr）+ `zpaq error: …` |
| `add <归档> <不存在的输入路径>` | **0** | 只有诊断，**无非 0 退出码** |
| 成功的 add / extract / list | 0 | —— |

所以在这个工具上，退出码既不能单独证明成功（存在"有诊断但返回 0"的路径），
也不能单独证明失败；错误路径的断言必须**诊断文本 + 退出码一起看**。

## 根因

本仓 L2 冒烟门禁的判据是 `bin/<tool> --version`（失败回退 `--help`）退出码为 `0`，
隐含假设"所有 CLI 都实现 GNU 风格版本开关"。zpaq 7.15（2016 年发布，
`zpaq command archive files... -options` 型命令行）没有这个开关。
把它判成失败会误伤一个完全正常的包；把它当通过又不能提供可用性证据。

## 影响范围

- 所有 `package_type = "application"` 的包，尤其是 2016 年前发布、
  非 GNU 风格参数解析的老式 CLI。
- 任何把 L2 结果直接当作"适配是否成功"证据的流程。
- 写 `set -euo pipefail` 测试脚本时注意：既有"期望失败但返回 0"的路径
  （断言要落在产物/诊断上），也有"期望失败且返回 2"的路径（缺失归档）——
  后者若不显式捕获 `$?`，`set -e` 会让脚本提前中断，须写成 `rc=0; cmd || rc=$?`。

## 附带实测（同一轮旁证）

`zpaq extract -to <dir>` 在 `<dir>` **不存在时会自行创建**（实测 `-to out1`
成功生成 `out1/src/...`），这正是上游 `make check` 的 `-to zpaq.new` 所依赖的行为；
不要把"输出目录必须先 mkdir"当默认。

## 推荐方案

**方法**: `assert-real-roundtrip-instead-of-version-flag`

1. **先实测再假设**：对上游工具分别跑 `--version` / `--help` / `-v` / 无参数，
   记录退出码与输出，不要默认"应该有版本开关"。
2. **不要为过门禁伪造 `--version`**：给上游打补丁改 CLI 语义与本次适配目的无关，
   会引入不必要的行为差异（本仓 R8/R10 口径）。
3. **用真实功能往返作为可用性证据**：`test_package` 对安装出来的二进制做
   `add -> extract -> 字节级 cmp`（与上游 `make check` 同口径），
   外加一次版本横幅断言（`zpaq v7.15` 字样证明二进制可执行、版本串正确）。
4. **如实记录特例**：在 `notes.md` 与 `manifest.yaml` 的 `validation` 段写明
   "L2 的 `--version` 判据对本包不适用"及原因，避免后续 reviewer / 审计
   把 CI 侧那条 non-blocking 警告误读成适配缺陷。

CI 侧 L2 本身是 `[warn] ... (non-blocking)`，不阻塞流水线；本地 `conan-verify`
在 application 包上会因 G4 `无法找到程序包 ID` 把 L2/L4/L5 记为
`⏭️ 跳过（无 cache 路径）`——**跳过不等于通过**，本包按"PASS 与 SKIP 并存时
以 SKIP 为准"的口径记录为未执行，并另附人工补测
（`reports/conan-verify-supplement.md`）。

## 验证命令

```bash
bash test_package/test.sh <pkg>/bin/zpaq
# RESULT: 7/7 checks passed
```

（解释器由 `test_package/conanfile.py` 解析：`$CONFIG_SHELL`
——`ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 已声明 —— 取不到时按固定候选清单
（`/data/service/hnp/bin/bash`、`/bin/bash`、`/usr/bin/bash`）用 `os.path.exists()` 探测，
都取不到则 `ConanException` 显式报错。**不要用 `shutil.which("bash")`**：实测它会命中
调用方运行时自带的 `/data/storage/el1/bundle/.../bash/bin/bash`，conan 起的
`/system/bin/sh` 执行它报 `Permission denied`，`conan create` 的 `test()` 直接
`Error 126` 中断。）

## 取证记录

- 包: zpaq 7.15（`archives/z/zpaq/7.15`）
- 逐字证据: `reports/test-report.md` §4、`reports/conan-create.log`（test_package 段）
