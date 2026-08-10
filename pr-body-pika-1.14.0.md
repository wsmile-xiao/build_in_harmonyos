- **三方库名称**：pika（PikaPython）
- **上游版本**：v1.14.0
- **上游仓库地址**：https://github.com/pikasTech/PikaPython
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（本地副本13 SKILL，含 knowledge/graph 知识图谱 E092/E165）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游 v1.14.0 release tarball 无 test/ 目录（无正式测试框架，测试依赖 pikaCompiler 预编译器生成的绑定，构建期生成） |
| 集成测试 | 0 | 来源：同上 |
| 其他测试 | 0 | |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 33 | +33 | 主机侧数据层 API 测试 33 条断言（arg/stack/strs/memory/平台内存接口），日志见 reports/host-test-log.txt |
| 集成测试 | 11 | +11 | test_package 消费者视角交叉测试（test.c，ohos-aarch64 交叉编译并在目标执行），11 条断言全部实际执行，11/11 通过 |
| 鸿蒙特有测试 | 0 | 新增 | 无系统同名库，无需 R26 静态隔离专项；R38 判断产物为纯静态库无需 commands.json |
| **合计** | **44** | **+44** | 全部为适配后补全（上游无正式测试用例） |

> 注：test.c 共 11 条 check 断言，全部实际执行（含 pika_platform_malloc 返回非 NULL 断言），11/11 通过。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心功能新增 44 条断言：主机侧数据层 API 单元测试 33 条 + test_package 交叉侧消费者测试 11 条
> - **补全原因**：上游 v1.14.0 release tarball 无 test/ 目录（上游 CI 依赖 pikaCompiler 预编译器在构建期生成绑定后测试，产物不在源码包内）；按 TEST_QUALITY_SPEC.md 自行补充
> - **新增测试文件清单**：
>   1. `archives/p/pika/1.14.0/test_package/test.c` — PikaPython 核心数据层 API 测试（arg_newInt/arg_newStr/Stack/strsCopy/pika_platform_malloc 等 11 条断言，全部实际执行）
>   2. `archives/p/pika/1.14.0/test_package/stubs.c` — 链接桩（pikaCompiler 构建期生成的 stdlib 绑定符号，测试数据层路径不触碰 VM/builtins，仅满足静态链接）
>   3. `archives/p/pika/1.14.0/test_package/MANIFEST.yml` — 测试声明文件（L0e 强制）
>   4. 主机侧 33 条断言测试日志：`archives/p/pika/1.14.0/reports/host-test-log.txt`

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（上游无正式测试用例，不适用）
- 新增测试用例通过率：44/44（100%）
  - 主机侧数据层 API 测试：33/33（100%）
  - test_package 交叉侧测试：11/11（100%）

## 补充说明

- **本地 CI 模拟预审通过**：`conan create`（ohos-aarch64 profile，交叉编译 + 目标执行测试）退出码 0，test_package 11/11 通过；W3 本地 CI 模拟结果写入 `.ci-result.json`（exit_code=0，含日志哈希）；W4 Pre-PR 独立审计 verdict=pass（P0=0，P1=0，2 个 P2/P3 均已修复并复验）。
- **适配要点**：上游 v1.14.0 无根级 CMakeLists.txt，补丁 0001 新增（编译 src/*.c 为静态库 pika-core，头文件安装至 include/pika）；补丁 0002 修复 clang 标签后声明语法错误（GCC 允许、clang 拒绝，9 个级联错误根因均为同一处）。
- **已知限制**：PikaPython 完整 VM 脚本执行需 pikaCompiler 预编译器生成的标准库绑定（New_builtins_object 等），本配方交付 pika-core 静态库及数据层 API 测试；如需完整 Python 脚本执行能力需另行打包 PikaStdLib 绑定（上游独立发布流程）。
- **零依赖**：PikaPython 纯 C 内核，无第三方依赖，W0 依赖检查通过。
- **GitHub 源码包** sha256 已核对：920dd983879f3fa1666a04b74a1c7704262273664d3ff8389d225aa9dcba8542。
