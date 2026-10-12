- **三方库名称**：raku-log
- **上游版本**：0.3.1
- **上游仓库地址**：https://git.tyil.nl/raku/log
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent（新增知识草稿 `knowledge/drafts/E543-draft-DBC4.kv`：Raku 6.d 模块在 OHOS 上的打包、运行时环境与 `Str.fmt` 模板分发缺陷）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游 v0.3.1 release tarball 与 Git tag 均不含测试目录 |
| 集成测试 | 0 | 上游未提供 |
| 其他测试 | 0 | 上游未提供 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 6 | +6 | `test_module.raku`：严重级别连续排序、role 一致性、共享实例初值、消费者实现与八级方法可调用性、`with` 守卫惯用法 |
| 集成测试 | 0 | 不变 | 纯 Raku 源码模块，无独立集成层 |
| 鸿蒙特有测试 | 5 | 新增 | `test_ohos.raku`：OHOS 内核识别（`$*KERNEL.name == 'harmonyos'`、HongMeng 内核版本、aarch64）与 HarmonyOS 缓存文件系统 UTF-8 往返 |
| **合计** | **11** | **+11** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 v0.3.1 的 release tarball 与 Git tag 均不包含任何测试文件或测试目录，因此不存在可修改的上游测试用例，也未遗漏任何上游测试。本包 `patches: {}`，上游源码原样打包，未做任何改动。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 `Log` / `Log::Implementation` / `Log::Level` 核心 API 新增 6 个单元断言，为 HarmonyOS 平台特性新增 5 个断言，合计 11 个断言。
> - **补全原因**：上游库为纯 Raku 6.d 模块，只发布源码与 `META6.json`，仓库内无正式测试框架与测试目录，无法执行任何上游测试。
> - **新增测试文件清单**：
>   1. `test_package/test_module.raku` — 6 个断言：`Log::Level` 严重级别取值连续且有序（0–7）、`Log::Implementation` 为可实现的 role、`$Log::instance` 初值为未定义（使文档中的 `with` 守卫成立）、消费者可实现 role 并收到消息、八个日志级别方法均可调用、`with $Log::instance` 惯用法可触达共享实例。
>   2. `test_package/test_ohos.raku` — 5 个断言：Raku 运行时识别 HarmonyOS 内核（`$*KERNEL.name == 'harmonyos'`）、内核版本含 `HongMeng`、目标架构为 `aarch64`、HarmonyOS 临时/缓存目录存在、HMDFS 上 UTF-8 内容往返一致。
>   3. `test_package/test_runner.py` — 消费侧测试入口（0 断言），通过 `subprocess` 启动打包后的 `raku` 可执行文件，注入 `RAKULIB`、`LD_LIBRARY_PATH`、`MVM_JIT_DISABLE=1`，并在可写临时目录中运行上述 `.raku` 测试脚本。
> - **鸿蒙特有测试的判定依据**：Linux 版 MoarVM 报告 `$*KERNEL.name` 为 `linux`，OHOS 版报告 `harmonyos`，故 `test_ohos.raku` 的前三个断言在通用 Linux 主机上必然失败，仅能在 OHOS 目标上通过——这是其"鸿蒙特有"属性的实证，而非仅靠文件名声明。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（上游未提供测试，不适用）
- 新增测试用例通过率：11/11（100%，在 OHOS 目标 profile `ohos-aarch64` 下）

**平台口径说明**：`test_ohos.raku` 由 `test_runner.py` 以 `os=OHOS` 为条件运行。因此上述 11/11 是 **OHOS 目标上的结果**；在非 OHOS 主机上仅运行 `test_module.raku`，为 6/6。

补充验证证据：

- Conan profile：`ci/conan/profiles/ohos-aarch64`（OHOS 6.0 / armv8 / clang 15）
- `conan create` 与测试包执行通过，包引用 `raku-log/0.3.1`
- 本地 CI 模拟（W3）全量门禁 L0–L5 通过：`.ci-result.json` `exit_code: 0`
- 运行时依赖为制品仓已发布的 `rakudo/2025.11`、`nqp/2025.11`、`moarvm/2025.11`（OHOS/aarch64）

## 补充说明

1. **运行时说明**：`raku-log` 是 Raku 6.d（`META6.json` 声明 `perl: 6.d`）模块库，Perl 5 不是兼容运行时。配方以 `self.requires("rakudo/2025.11", run=True)` 引用制品仓已发布的 OHOS Rakudo/MoarVM 运行时，不伪造本地原生编译步骤。
2. **源码未改动**：本包无补丁（`patches: {}`），上游源码按原样打包为 `.rakumod` 与 `META6.json`，并显式排除 `.precomp/**` 预编译缓存。
3. **产物类型**：纯模块包，不产生可执行文件（`cpp_info.bindirs = []`），因此按 R38 不提供 `commands.json`。
4. **settings 精简**：本包不编译任何代码，产物完全由 `os`/`arch` 决定，故配方仅声明 `settings = "os", "arch"`，避免同一份源码被无意义地按 `build_type`/`compiler` 拆分成多个变体。
5. **已知限制一（上游缺陷）**：`Log::Implementation` 的模板分发候选方法以 `$template.fmt(|@args)` 委托，而 Raku 的 `Str.fmt` 将首个位置参数视为**格式串**而非取值，故 `'value %d'.fmt(42)` 会抛出 `Your printf-style directives specify 0 arguments, but 1 argument was supplied`（`sprintf` 则可正常工作）。该调用路径属上游缺陷，未被本次测试覆盖，已在 `reports/test-report.md` 与知识草稿中记录；未修改上游源码。
6. **已知限制二（覆盖缺口）**：测试入口固定 `MVM_JIT_DISABLE=1`，因此验证的是 MoarVM 解释器路径；配方未对消费者强制该变量（避免经共享运行时波及无关包），故 OHOS 上 JIT 开启的默认执行路径未被本测试覆盖。
7. **已知限制三（上游无测试基线）**：上游无测试，无法给出"上游测试通过率"的真实数值，故按 0/0 如实标注为不适用。
8. **源码地址**：上游项目自建 forge `git.tyil.nl` 的官方快照地址，SHA256 `7c5837fe116bcaa1710fc65ed7e2987272c1368c5e3943691fddaa638cf2b8dc`。快照 URL 本身不具备不可变性，已以 sha256 钉定。
