# DRAFT-E321-cmake4-policy-version-minimum：DRAFT-E321-cmake4-policy-version-minimum

> Status: **Draft**（待审核 promote）| severity: `2` | category: `toolchain|cmake` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-E321-cmake4-policy-version-minimum.kv`

---

## 触发面

- trigger_tool: `cmake|conan`
- phase: `configure`

**匹配关键词**：cmake_minimum_required,compatibility,removed,cmake 4

## 错误签名（error_signature）

```text
Compatibility with CMake < 3\.5 has been removed|cmake_minimum_required\(VERSION 3\.[0-4]|CMake Error.*compatibility
```

## 根因（root_cause）

CMake 4.x 移除了对 <3.5 的兼容策略；大量老项目（尤其声明 3.3/3.5 的）在 configure 阶段直接被拒绝。修复变量 CMAKE_POLICY_VERSION_MINIMUM 必须在 cmake_minimum_required() 执行 前生效。Conan 的 tc.variables 写入 conan_toolchain.cmake（在项目 CMakeLists 的 cmake_minimum_required 之后才被 include），无效；cache_variables 走 -D 命令行参数， 在任何 CMakeLists 解析前生效，有效

## 影响范围（affected_scope）

所有 cmake_minimum_required(<3.5) 的老项目在 CMake 4.x 工具链下的交叉编译； OHOS SDK 当前 CMake 4.1.2 必然触发

## 推荐方案（rec_approach: `conanfile 用 cache_variables 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5（切勿用 tc.variables，其写入 toolchain 文件在 cmake_minimum_required 之后加载不生效）`）

conanfile 用 cache_variables 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5（切勿用 tc.variables，其写入 toolchain 文件在 cmake_minimum_required 之后加载不生效）

## 补充关键词

cmake_minimum_required, policy, VERSION_MINIMUM, CMake 4, compatibility, 3.3, 3.5

---

*本文件由 `knowledge/drafts/DRAFT-E321-cmake4-policy-version-minimum.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
