- **三方库名称**：cgicc
- **上游版本**：3.2.19
- **上游仓库地址**：https://ftp.gnu.org/gnu/cgicc/cgicc-3.2.19.tar.gz（GNU 官方发布，https://www.gnu.org/software/cgicc/）
- **适配路径**：路径 B（贡献创新，新增知识库草稿：Makefile 硬编码 -lstdc++ 在 OHOS libc++ 工具链下的修复模式）
- **使用知识库**：openharmony-compile-agent（E007/E072 config.guess HarmonyOS、E011/E052/E112 configure 临时目录、E519 out-of-source srcdir、E455 libcxx 工具链；新增草稿 DRAFT-cgicc-3.2.19-libstdcxx-hardcode-to-libcxx）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游 tarball `./test/` 目录为空，Makefile.am 未注册 TESTS/check_PROGRAMS |
| 集成测试 | 0 | 来源：`make check` 实测无任何测试用例运行（exit 0，无 PASS/FAIL 输出） |
| 其他测试 | 0 | — |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试，未新增单元测试 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.cpp 消费者测试（4 断言：Cgicc 构造、getRequestMethod、HTMLDoctype/HTTPHTMLHeader 渲染非空） |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：test_package 消费者测试（Conan L1），验证被测库可被下游 C++ 项目链接与调用
> - **补全原因**：上游 tarball `./test/` 目录为空、无正式测试框架，按 R34/R51 以真实消费者视角补全 L1 测试
> - **新增测试文件清单**：
>   1. `archives/c/cgicc/3.2.19/test_package/test.cpp` — 调用 cgicc 公开 API（Cgicc/CgiEnvironment/HTMLDoctype/HTTPHTMLHeader）并断言渲染输出非空
>   2. `archives/c/cgicc/3.2.19/test_package/MANIFEST.yml` — 上游测试清点声明（无注册测试）

## 验证结果

- 编译状态：通过（conan-verify G0-G4 + L2/L4/L5 全绿；W3 本地 CI 模拟 Pass rate 100% (1/1)）
- 上游测试用例通过率：0/0（上游无注册测试，`make check` 实测无用例）
- 新增测试用例通过率：1/1（100%，本地编译运行 PASS：4 断言全过）

## 补充说明

- 官方来源核验：GNU FTP tarball SHA-256 `2a17b976248de03447f9e36d6ce18a80749990d8543e2dfeea09c413eb67f7f0`；gpg 签名校验因本机无 gpg 命令跳过（平台限制，SHA-256 已与官方一致）。
- 适配补丁 7 个（全部平台适配，无 `__OHOS__` 宏）：
  1. `-lstdc++` → `-lc++`（OHOS 工具链仅 libc++，无 libstdc++）
  2. configure 临时目录 umask 077 → 002（HMDFS 下 0700 目录不可写）
  3. doc/Makefile html-doc 资源加 `$(srcdir)/` 前缀、install-data-local 改遍历 `$(builddir)/html`（conan out-of-tree 构建）
  4. config.guess 识别 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`
  5. config.sub 识别 `linux-ohos*` 三元组
- 路径 B 知识草稿：`knowledge/drafts/DRAFT-cgicc-3.2.19-libstdcxx-hardcode-to-libcxx.{md,kv}`（问题/根因/方案/验证/适用边界/反例齐备），与本库归档同一 PR。
- 知识查重结论：config.guess/configure 临时目录/out-of-source 三类错误分别等价命中 E007/E072、E011/E052/E112、E519（走路径 A 复用）；仅 `-lstdc++` 硬编码模式无等价条目且可跨库复用，故走路径 B 新增草稿。
- W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger`（origin/main 基线中其他库已跟踪隐藏文件）：已按执行端基线规则做临时 index 隔离复验 W3，并已无条件恢复（index blob 与 origin/main 一致、工作区文件完整、git status 干净）。
- 已知限制：gen_summary 报 `'str' object has no attribute 'append'` 系 qpdf 等既有 manifest 引发的工具问题（非本库缺陷，非阻塞）。