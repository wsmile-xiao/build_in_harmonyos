<!--
PR 标题规范（Conventional Commits + 三方库名）

格式：<type>(<库名>): <版本> <简要描述>

type 取值:
  feat  — 新增三方库适配         示例: feat(sqlite3): 3.49.1 适配 HarmonyOS PC
  fix   — 修复已有配方编译问题    示例: fix(openssl): 1.1.1 修复 aarch64 链接错误
  chore — 版本升级/维护           示例: chore(zlib): 1.3.1 版本升级
  docs  — 知识图谱/文档更新      示例: docs(knowledge): 新增 E012 静态库链接经验

规则:
  1. type 必须小写，取值仅限上表四种
  2. scope = 三方库名（小写，与 archives/ 目录名一致）
  3. 版本号紧跟 scope 后
  4. 描述用中文，简洁明了（≤20字）
  5. 不加活动标签、不加 emoji
  6. commit message 与 PR title 保持一致
-->

## PR 信息
- **三方库名称**：{{SOFTWARE}}
- **上游版本**：{{VERSION}}
- **上游仓库地址**：{{UPSTREAM_URL}}
- **适配路径**：{{ADAPTATION_PATH}}
- **使用知识库**：{{KNOWLEDGE_BASE}}

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | {{UPSTREAM_UNIT_TESTS}} | {{UPSTREAM_UNIT_DESC}} |
| 集成测试 | {{UPSTREAM_INTEGRATION_TESTS}} | {{UPSTREAM_INTEGRATION_DESC}} |
| 其他测试 | {{UPSTREAM_OTHER_TESTS}} | {{UPSTREAM_OTHER_DESC}} |
| **合计** | **{{UPSTREAM_TOTAL_TESTS}}** | |

### 是否存在对上游测试用例的修改？
{{TEST_MODIFICATION_ANSWER}}

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | {{ADAPTED_UNIT_TESTS}} | {{ADAPTED_UNIT_COMPARE}} | {{ADAPTED_UNIT_DESC}} |
| 集成测试 | {{ADAPTED_INTEGRATION_TESTS}} | {{ADAPTED_INTEGRATION_COMPARE}} | {{ADAPTED_INTEGRATION_DESC}} |
| 鸿蒙特有测试 | {{HARMONYOS_TESTS}} | {{HARMONYOS_TESTS_COMPARE}} | {{HARMONYOS_TESTS_DESC}} |
| **合计** | **{{ADAPTED_TOTAL_TESTS}}** | {{ADAPTED_TOTAL_COMPARE}} | |

---

## 上游测试用例修改说明
{{TEST_MODIFICATION_DETAIL}}

## 验证结果

### 编译验证
- 编译器: {{COMPILER}}
- 编译状态: {{BUILD_STATUS}}
- 构建系统: {{BUILD_SYSTEM}}
- 配置选项: `{{CONFIGURE_OPTIONS}}`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | {{CHECK_COMPILE}} | {{CHECK_COMPILE_DETAIL}} |
| 产物存在性 | {{CHECK_ARTIFACT}} | {{CHECK_ARTIFACT_DETAIL}} |
| ELF 格式 | {{CHECK_ELF}} | {{CHECK_ELF_DETAIL}} |
| 运行测试 | {{CHECK_RUN}} | {{CHECK_RUN_DETAIL}} |
| 动态依赖 | {{CHECK_DEPS}} | {{CHECK_DEPS_DETAIL}} |

### 补丁说明
{{PATCH_DESCRIPTION}}

### 依赖
{{DEPENDENCIES}}

### 测试结论
- 总体评价: {{TEST_CONCLUSION}}
- 已知限制: {{KNOWN_LIMITATIONS}}

### 遇到的问题与解决方案
{{ISSUES_AND_SOLUTIONS}}

### 验证命令
```
{{VERIFICATION_COMMANDS}}
```
