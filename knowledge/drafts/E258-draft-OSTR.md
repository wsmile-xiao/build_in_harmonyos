# E258 - monorepo 包的 PR 说明应把包内 smoke-test 与 repo 级测试簇分开列出

> **结构化数据**: [E258-draft-OSTR.kv](E258-draft-OSTR.kv)
> **类别**: testing/evidence-boundary/review | **严重度**: 🟡 | **阶段**: testing/ci/review

## 症状
PR 只写“执行了一个 smoke-test”，审查会认为上游测试少报。

## 根因
单包 Conan 适配只拥有自己的可执行入口，但上游 monorepo 还包含控制面、前端和基础设施测试簇。

## 修复
1. 保留完整上游分母。
2. 单列包内实际执行的 smoke-test 和 test_package。
3. 对 control-plane/tests、tests、web/dashboard/tests、infrastructure scripts 逐条说明未运行原因。

## 验证
- `components/ostra-sysctl/tests/smoke-test.sh` 实际执行
- `test_package` 实际执行
- 其余测试簇留在包外说明，不混入当前 Conan 包通过率

## 关系
- `similar_to -> E257`
- 这条关注的是 PR 口径与审查表达，不是具体 shell 兼容性。
