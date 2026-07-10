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
