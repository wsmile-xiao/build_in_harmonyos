- **三方库名称**：retry（重复执行命令直到满足条件的命令行工具；stdin 捕获重放、失败尝试 stdout 转 stderr）
- **上游版本**：1.0.6
- **上游仓库地址**：https://github.com/minfrin/retry（发布源 `https://github.com/minfrin/retry/releases/download/retry-1.0.6/retry-1.0.6.tar.gz`，官方 HTTPS 源，sha256 `c208baf759134da27012042ccc30df7d995ed038d7d5602db7dbda3becb34827` 已实测校验）
- **适配路径**：路径 A（基础适配，3 个可移植性补丁）
- **使用知识库**：知识图谱命中/参考 E007（config.guess 不识别 HarmonyOS）、E011（HMDFS 上 `umask 077` 临时目录不可写）；适配知识另沉淀于版本级 `manifest.yaml` 的 `knowledge_gained`（5 条）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试/回归 | 0 | 来源：清点证据见下（无 tests/ 目录；`Makefile.am` 仅 `bin_PROGRAMS = retry`，无 `TESTS`/`check_PROGRAMS`/`check-local`；`configure` 无测试开关） |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | `make check` 实测为 automake 空目标，执行 0 用例（rc=0） |
| **合计** | **0** | 上游 1.0.6 不含任何测试套件 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试（全量执行） | 0 | 不变（上游本无测试） | `build()` 仍执行 `make check` 并在构建日志中留下"0 用例"证据 |
| 鸿蒙特有测试（消费者视角） | 28 | **新增** | `test_package/test_retry.sh` 真实执行已安装的 `retry` 二进制，28/28 通过 |
| **合计** | **28** | **+28** | 覆盖条件重试/退出码/stdin 重放/stdout 路由/错误路径 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 1.0.6 不含任何测试套件可改；本次适配未改动任何上游文件（3 个补丁全部为构建基础设施的
> 可移植性修复，见下）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **上游测试清点证据（R51）**：解压树（28 个文件）无 `tests/`/`test/`/`Test/` 目录，
>   `find . -iname '*test*' -o -iname '*check*'` 无结果；`Makefile.am` 仅 `bin_PROGRAMS = retry`；
>   `grep -c 'enable.*test' configure` = 0；`make check` 实测 rc=0、0 用例。完整申报表见
>   `1.0.6/test_package/MANIFEST.yml` 与 `1.0.6/notes.md`。
> - **补全的测试范围**：核心行为 28 条 TAP 断言 —— 条件重试（`--until=success/fail`、`--while=fail`）、
>   `--times` 耗尽与 `giving up`、退出码透传（42）、stdin 捕获并逐次重放到重试尝试、失败尝试 stdout
>   不泄漏到 stdout、非法参数与不可执行命令的报错路径、`-m` 自定义退避消息。
> - **补全原因**：上游无测试套件，需由消费者视角验证安装后二进制的可用性与文档行为一致性。
> - **新增测试文件清单**：
>   1. `archives/r/retry/1.0.6/test_package/test_retry.sh` — 28 条 TAP 断言，真实执行已安装二进制
>   2. `archives/r/retry/1.0.6/test_package/conanfile.py` — `test()` 通过 `self.run("sh test_retry.sh")` 执行
>   3. `archives/r/retry/1.0.6/test_package/MANIFEST.yml` — 上游测试清点证据 + 断言计数声明（28）

## 验证结果

- 编译状态：**通过**（`conan-verify` G0–G4 与 L2/L4/L5 全 PASS；`finish` W3 本地 CI 阻塞门禁 PASS，`conan create` EXIT=0，profile `ohos-aarch64-device`）
- 上游测试用例通过率：**0/0（上游无测试套件，附清点证据）**
- 新增测试用例通过率：**28/28（100%）**
- 本地 CI 等价门禁：L0 pass / L1 pass（含 L1a/L1b/L1c 与 L1e 破坏性反向验证）/ L2 pass / L5 pass；L4 为补丁文本扫描的已知良性命中（`config.guess`/`config.sub` 的 shell 片段，无危险调用），非阻断

## 补充说明

### 适配要点

1. **构建链**：官方 release tarball 自带生成的 Autotools 树（`configure`/`Makefile.in`/`config.h.in`），
   `AutotoolsToolchain` + `autotools.configure()/make()`（`make -j1`，R9）交叉编译；
   产物 `bin/retry` 与 `share/man/man1/retry.1`。
2. **补丁 0001（config.guess）**：2018 年版 `config.guess` 不认识 `uname -s = HarmonyOS`；
   native 构建（build == host）时 AutotoolsToolchain 不传 `--host/--build` 三元组，configure 必然报
   `cannot guess build type; you must specify one`。补 HarmonyOS 分支输出 `aarch64-unknown-linux-ohos`。
3. **补丁 0002（config.sub）**：同版本 `config.sub` 未收录 `ohos`，交叉构建 `--host=aarch64-linux-ohos`
   与三字段形式均无法 canonicalize（且其 `linux*)` 兜底会把 `-linux-ohos` 误改写为 `-linux-gnu-ohos`）。
   在 `maybe_os` 列表与大 OS 列表两处补 `linux-ohos*`（纯 POSIX 修复）。
4. **补丁 0003（configure umask）**：configure 以 `umask 077` 创建 config.status 临时目录，HMDFS
   UID 映射下目录对构建进程不可写（E011）——放宽为 `umask 022`（与 aaphoto/lrcalc 同一已验证先例）。
5. **无平台宏**：3 个补丁均为可移植性修复，不注入 `__OHOS__`/`-D__OHOS__`（R8/PF5），
   `patches/` 全量扫描无强绑定宏。
6. **零依赖**：`requires` 为空（W0 检查：configure.ac 无 `AC_CHECK_LIB`/pkg-config 依赖，仅系统 libc）。
7. **CLI 声明**：软件级 `commands.json`（R38，`type=tool`，`ref=retry/1.0.6`）。

### 已知限制

| 项 | 技术原因 |
|----|----------|
| 上游零测试 | 回归保护依赖本 PR 新增的 `test_package/test_retry.sh`（28 断言）；上游若后续补齐套件可直接接入 |
| 自动化中的 stdin | `retry` 设计上捕获 stdin 并在重试时重放；脚本中调用需按需 `</dev/null`（上游行为，非缺陷） |

### 验证证据

| 证据 | 位置 |
|------|------|
| 上游清点（0 用例）+ 新增 28/28 明细 | `1.0.6/reports/test-report.md` |
| 本地 CI 全门禁日志（含 conan create 内 test_package 28/28） | `1.0.6/reports/w3-local-ci.log` |
| conan-verify 报告（G0–G4/L2/L4/L5 PASS） | `1.0.6/reports/conan-verify-report.md` |
| 适配笔记（问题、补丁、R51 申报表） | `1.0.6/notes.md` |
