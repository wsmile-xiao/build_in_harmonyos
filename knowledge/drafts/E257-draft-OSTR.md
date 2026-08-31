# E257 - ostra 上游测试统计应按“测试相关文件 + 包内可执行入口”分层记录

> **结构化数据**: [E257-draft-OSTR.kv](E257-draft-OSTR.kv)
> **类别**: testing/evidence-boundary/ci | **严重度**: 🟡 | **阶段**: testing/ci

## 症状
PR 里只写一个 smoke-test，审查就会认为上游测试被少报；但上游仓库还包含 control-plane、web 和 infrastructure 相关测试/脚本文件。

## 根因
`components/ostra-sysctl` 只覆盖 ostra 的 sysctl 组件，不能把 monorepo 里其他子系统的测试都算成当前 Conan 包的可执行范围。

## 修复
1. 先统计上游测试相关文件总数。
2. 再单列本包实际执行的上游子集。
3. 最后把 HarmonyOS `test_package` 作为新增验证单独列出。
4. 未运行项按 FastAPI / DB / web / infra / runtime 边界说明原因。

## 验证
- `components/ostra-sysctl/tests/smoke-test.sh` 实际执行
- `test_package` 实际执行
- 其余 22 项保留为包外不运行

## 关系
- `similar_to -> E255, E256`
- 这条关注的是审查证据口径，不是 shell 兼容性。
