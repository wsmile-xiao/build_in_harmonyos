- **三方库名称**：runlim（采样并限制程序及其子进程时间/内存用量的命令行工具）
- **上游版本**：1.10
- **上游仓库地址**：https://fmv.jku.at/runlim/（官方发布源 `https://fmv.jku.at/runlim/runlim-1.10.tar.gz`，官方 HTTPS 源，sha256 `619aec701e9984977832e2db2bf05cef82ad6ac4ca53b595863bec115b69bc33` 已实测校验）
- **适配路径**：路径 A（基础适配，1 个 RLIMIT_AS 单位修复补丁）
- **使用知识库**：知识图谱无直接命中条目（新增知识沉淀于版本级 `manifest.yaml` 的 `knowledge_gained` 5 条：RLIMIT_AS 单位缺陷、OHOS `/proc/<pid>/stat` 布局核验、runlim 状态码语义、makefile.in 内联 `@CC@/@CFLAGS@`、上游无测试清点）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：解压树（8 文件）无 tests/ 目录；`find . -iname '*test*' -o -iname '*check*'` 无结果 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | `makefile.in`（全文 5 行）仅 runlim/clean 两目标；`configure.sh`（43 行）仅 -h/--help/-g；实测 `make check` → "No rule to make target 'check'" |
| **合计** | **0** | 上游 1.10 不含任何测试套件 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试（全量执行） | 0 | 不变（上游本无测试） | 无 check 目标可执行，清点证据见 MANIFEST.yml |
| 鸿蒙特有测试（消费者视角） | 31 | **新增** | `test_package/test_runlim.sh` 真实执行已安装的 `runlim` 二进制，31/31 通过 |
| **合计** | **31** | **+31** | 覆盖限制行为（-t/-r/-s）、信号状态、日志、错误路径与状态码语义 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 1.10 不含任何测试套件可改；本次适配未改动任何上游测试文件（唯一的源码补丁为
> RLIMIT_AS 单位修复，见下）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **上游测试清点证据（R51）**：解压树无 `tests/`/`test/`/`Test/` 目录；`makefile.in` 全文
>   5 行仅 runlim/clean；`configure.sh` 无测试开关；`make check` 实测 "No rule to make target"。
>   完整申报表见 `1.10/test_package/MANIFEST.yml` 与 `1.10/notes.md`。
> - **补全的测试范围**：核心行为 31 条 TAP 断言 —— 版本/用法/参数错误路径；pass-through 与
>   `-o` 日志内容；runlim 状态码语义（子进程退出码被忽略）；`-r`/`-t`/`--time-limit`/
>   `--real-time-limit` 时间限制；`-s`/`--space-limit` 采样内存限制；子进程 SIGSEGV 状态（rc=4）；
>   `-k` 信号传播（128+11）；默认日志到 stderr。其中 `-t` 用例是 RLIMIT_AS 单位修复的回归用例。
> - **补全原因**：上游无测试套件，需由消费者视角验证安装后二进制的可用性与文档行为一致性。
> - **新增测试文件清单**：
>   1. `archives/r/runlim/1.10/test_package/test_runlim.sh` — 31 条 TAP 断言，真实执行已安装二进制
>   2. `archives/r/runlim/1.10/test_package/conanfile.py` — `test()` 通过 `self.run("sh test_runlim.sh")` 执行
>   3. `archives/r/runlim/1.10/test_package/MANIFEST.yml` — 上游测试清点证据 + 断言计数声明（31）

## 验证结果

- 编译状态：**通过**（`conan-verify` G0–G4 全 PASS；本地 CI 门禁 L0/L1/L1e/L2/L4/L5 PASS，`conan create` EXIT=0，profile `ohos-aarch64-device`）
- 上游测试用例通过率：**0/0（上游无测试套件，附清点证据）**
- 新增测试用例通过率：**31/31（100%）**

## 补充说明

### 适配要点

1. **构建链**：官方 tarball 为 `configure.sh` + `makefile.in` 的极简 POSIX 构建；`build()` 以
   Conan conf 的 clang 作为 `$CC`、`-O2 -DNDEBUG` 作为 `$CFLAGS` 经 configure.sh 生成 makefile
   （R33：编译器来自 Conan conf，不用裸 shell 变量；R5：configure.sh 用 profile 的 CONFIG_SHELL 执行），
   再 `make -j1`（R9）单次编译；上游无 install 目标，`package()` 直接拷贝 `bin/runlim` 与
   `licenses/LICENSE`。
2. **补丁 0001（RLIMIT_AS 单位修复）**：`space_limit`（MB）被原样当字节传给内核，
   `-t`/`--time-limit`（及 `-t -s` 组合）触发 setrlimit 后子进程 `execvp` 恒失败 ENOMEM（rc=1
   "execvp failed"）；改为按字节换算 `((rlim_t) space_limit << 20)`。设备最小复现与修复后
   回归（rc=1 → rc=2 "out of time"）见 `reports/test-report.md` 第四节；该用例已固化为 test_package
   第 19/20 条断言。
3. **无平台宏**：补丁为纯单位修复，不注入 `__OHOS__`/`-D__OHOS__`（R8/PF5）。
4. **零依赖**：`requires` 为空（W0 检查：源码仅 POSIX/libc 头文件，无 pkg-config/AC_CHECK_LIB）。
5. **/proc 兼容性核验**：HongMeng Kernel 1.12 的 `/proc/<pid>/stat` 字段布局与标准 Linux 一致
   （vsize=field 23 字节、rss=field 24 页），采样解析无需适配（对照证据见 `reports/test-report.md` 第四节）。
6. **CLI 声明**：软件级 `commands.json`（R38，`type=tool`，`ref=runlim/1.10`）。

### 已知限制

| 项 | 技术原因 |
|----|----------|
| 上游零测试 | 回归保护依赖本 PR 新增的 `test_package/test_runlim.sh`（31 断言）；上游若后续补齐套件可直接接入 |
| 子进程退出码不转发 | 上游设计：返回 runlim 自身状态码（0/1/2/3/4/5/6/7/11），消费脚本需自行包裹 |
| 需要 /proc | Linux/OHOS 风格 procfs；无 /proc 环境不可用（上游设计） |

### 验证证据

| 证据 | 位置 |
|------|------|
| 上游清点（0 用例）+ 新增 31/31 明细、本地 CI 门禁与 conan create 内 test_package 31/31 | `1.10/reports/test-report.md` |
| conan-verify 报告（G0–G4 PASS） | `1.10/reports/conan-verify-report.md` |
| 上游测试清点（0 用例）与 31 条断言声明 | `1.10/test_package/MANIFEST.yml` |
| 适配笔记（问题、补丁、R51 申报表、修复前后实测） | `1.10/notes.md` |
