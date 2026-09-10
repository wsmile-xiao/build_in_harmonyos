## PR 信息

- **三方库名称**：wxwidgets
- **上游版本**：v3.3.3（Conan 修订版本 `3.3.3.1`）
- **上游仓库地址**：https://github.com/wxWidgets/wxWidgets
- **适配路径**：路径 A（基础适配）
- **使用知识库**：wxWidgets 3.3.3 已验证适配记录、CMake OHOS toolchain 经验、capability-probe/expected-skip 测试口径

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 429 | wxWidgets 3.3.3 Catch2 `test_base` 的 OHOS 有序清单；清单 SHA-256：`2214c00249801b8f0b2b1b7b72c6fdf6c00217d32da3a3b777c2d8afabe73ebe` |
| 集成测试 | 0 | 上游 wxBase 变体未注册独立集成测试；CTest 仅注册 1 个 `test_base` 驱动，不重复计数 |
| 其他测试 | 0 | Conan `test_package` 作为消费者验证单独记录，不计入上游分母 |
| **合计** | **429** | 目标端实际通过/跳过结果须由本版本新的 W3 回填 |

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（详见下方）

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 429 | 不变 | 保留完整上游清单；能力缺失仅允许产生带 reason 的受控 expected-skip |
| 集成测试 | 0 | 不变 | CTest 的 1 个驱动不重复计入用例总数 |
| 鸿蒙特有测试 | 6 | +6 | Conan `test_package` 在 HarmonyOS PC 上验证初始化、字符串、分词、URI、缓冲区和版本 API，共 6 项独立断言 |
| **合计** | **435** | **+6** | 429 个上游条目 + 6 个 HarmonyOS PC consumer 断言；本版本实测结果待 W3 回填 |

---

## 上游测试用例修改说明

1. **修改的测试文件**：`tests/file/dir.cpp`、`tests/filename/filenametest.cpp`、`tests/fswatcher/fswatchertest.cpp`
   - **修改原因**：目标端文件系统能力存在差异。
   - **修改内容**：保留原测试与断言；能力确实不可用时输出包含 id、path、reason 的 expected-skip marker。
2. **修改的测试文件**：`tests/intl/intltest.cpp`、`tests/mbconv/convautotest.cpp`、`tests/mbconv/mbconvtest.cpp`、`tests/strings/numformatter.cpp`、`tests/xml/xmltest.cpp`
   - **修改原因**：locale、编码和 XML 行为需要在目标运行时探测，不能假设目标 libc 与桌面平台一致。
   - **修改内容**：使用通用 POSIX/运行时能力探测及受控子进程边界；保留 reason-bound skip 计数，补丁中未新增 `__OHOS__` 条件宏。
3. **补充说明**：上游 Catch2 清单保持 429 项不变；适配新增的 Conan `test_package` 作为 6 项 HarmonyOS PC 消费者断言单独计入。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

上游已有 429 个 Catch2 测试条目。新增的 6 项 `test_package` 断言属于 HarmonyOS PC
消费者验证，用于验证 Conan 包的可发现性、链接和核心 wxBase API，不替代或删减上游测试。

## 验证结果

### 编译验证

- 编译器：HarmonyOS Clang/Clang++（W3 待执行）；Apple Clang 仅作补充验证
- 编译状态：macOS 补充编译通过；HarmonyOS PC W3 待执行
- 构建系统：CMake
- 配置选项：`-DBUILD_SHARED_LIBS=OFF -DwxBUILD_SHARED=OFF -DwxBUILD_TESTS=CONSOLE_ONLY -DwxUSE_GUI=OFF -DwxBUILD_PRECOMP=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5`

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | 待完成 | macOS 补充编译通过；不能替代 HarmonyOS PC 的干净 `conan create` |
| 产物存在性 | 待完成 | 等待 W3 对目标端静态 wxBase 产物核验 |
| ELF 格式 | 待完成 | 等待 W3 核验目标架构与 OHOS ABI |
| 运行测试 | 待完成 | 429 个 Catch2 条目、CTest 驱动和 consumer 测试均须在本版本 W3 实测 |
| 动态依赖 | 待完成 | 等待 W3 核验；配方声明静态构建且无 Conan 前置依赖 |

### 补丁说明

- 复用 wxWidgets 3.3.3 已验证的 20 个补丁，修订版本不改变上游源码版本。
- patch-ng、GNU patch（fuzz 0）和 git apply 三套引擎均成功重放 20/20。
- 三套结果树均为 9776 个文件，聚合 SHA-256 均为 `9ca450197ca9219a59fd265decbce4bda0028be593d60cc7e8fc1851f26c5668`。
- 补丁覆盖 CMake 能力探测、日期/locale 兼容、测试运行时能力探测和 Catch2 输出稳定性；未在补丁中新增 OHOS 平台宏分支。

### 依赖

- Conan 前置依赖：无（`requires=[]`）。
- 2026-09-08 实时查询主制品仓，仅存在 `wxwidgets/3.2.10`、`wxwidgets/3.3.3`，未发现 `wxwidgets/3.3.3.1`，版本号未占用。
- 官方源码为 GitHub Release asset `471278068`，SHA-256：`81b09d6dd9f1ed9301f8c55a968a488d0491f264dc2bab19a7e407ac67009482`。

### 测试结论

- 总体评价：配方、来源、补丁、测试清单和本地补充编译已完成准备；HarmonyOS PC W3、独立 W4 审计和 CI 尚未完成，因此当前不得声明目标平台验证通过。
- 已知限制：仅交付静态 wxBase 非 GUI 组件，不宣称 wxCore 图形窗口栈已适配；macOS 枚举出 467 个平台相关条目，与 OHOS 锁定的 429 个条目不同，审计按预期停止，未放宽目标端清单契约。

### 机器审查汇总字段

- 编译状态：待验证（macOS 补充编译通过；HarmonyOS PC W3 因历史 worker 连接超时尚未执行）
- 上游测试用例通过率：0/429（0%，HarmonyOS PC W3 尚未执行，禁止复用 wxwidgets/3.3.3 的历史结果）
- 新增测试用例通过率：0/6（0%，HarmonyOS PC `test_package` 尚未执行）

### 遇到的问题与解决方案

1. 历史 HarmonyOS worker `10.62.148.108:2222` 连接超时，因此没有生成或伪造 `.ci-result.json`，W3 保持待执行。
2. 当前主仓 preflight 存在 PF8/PF9 冲突：配方含 `bindirs` 时 PF8 要求更新软件级 `commands.json`，PF9 又按版本目录深度拒绝该文件。本分支保留 R38 要求的命令元数据且未使用绕过参数，提交前需由可用流程确认例外或修复门禁。

### 验证命令

```bash
# 完整收尾（内部执行 W2 与 HarmonyOS PC W3，并自动生成可信验证记录）
python3 "$SKILL_ROOT/scripts/ohc-run.py" finish wxwidgets 3.3.3.1 built

# PR 提交（内部先执行独立 W4，再推送、创建 PR 并监控检视与 CI）
python3 "$SKILL_ROOT/scripts/ohc-run.py" submit wxwidgets 3.3.3.1
```

## 提交信息

- 建议 PR 标题：`【积分赛】feat(wxwidgets): 3.3.3.1 适配 HarmonyOS PC`
- 源分支：`songzhenyan:feat/wxwidgets-3.3.3.1`
- 目标分支：`OpenHarmonyPCDeveloper/build_in_harmonyos:main`
- 当前提交：以推送时该分支的 `HEAD` 为准
- 关联 PR：`OpenHarmonyPCDeveloper/build_in_harmonyos#8925`
- 远端分支：`songzhenyan/build_in_harmonyos:feat/wxwidgets-3.3.3.1`
