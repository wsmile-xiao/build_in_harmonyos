# DRAFT-mbits-semver-0.1.1-coveralls-submodule-missing-tarball：CMake 覆盖率工具子模块不在官方 tag tarball 中——仅覆盖率用途的子模块可配方侧选项关闭，测试另行台账运行

> Contributor: pc4-36 | Status: Draft | Updated: 2026-09-22
> Source: mbits-semver 0.1.1 适配（task mbits-semver-0.1.1-r01-pc4-36）
> 对应：`knowledge/drafts/DRAFT-mbits-semver-0.1.1-coveralls-submodule-missing-tarball.kv`

## 现象

配置阶段直接阻塞：

```text
CMake Error at CMakeLists.txt:37 (include):
  include could not find requested file:
    tools/coveralls/Coveralls.cmake
```

## 根因

GitHub/Gitee 的 tag tarball 只打包 `.gitmodules` 声明，**不包含子模块内容**。
上游 CMakeLists 在测试/覆盖率选项开启时（如 `SEMVER_TESTING=ON`，standalone 默认）`include` 子模块内的 `.cmake` 文件，配置即失败。

与 **E150**（构建必需子模块缺失）的关键区别：

| 维度 | E150（构建必需） | 本模式（仅覆盖率工具） |
|------|------------------|------------------------|
| 子模块用途 | 参与库本体编译 | 仅测试覆盖率上报 |
| 处理 | 必须拉取子模块（manual-download） | 可配方侧选项关闭 + 测试另行台账运行 |
| 对上游测试影响 | 直接阻塞 | 不影响测试可执行性 |

## 修复

`conanfile.py` 的 `generate()` 置对应选项 OFF：

```python
tc.variables["SEMVER_TESTING"] = "OFF"
```

上游测试用例按双口径台账单独枚举运行，不做空壳跳过。

## 验证

- 置 `SEMVER_TESTING=OFF` 后 `conan create` G2 PASS
- 上游 `semver.exit` 测试在台账独立运行 1/1 Passed

## 适用边界 / 反例

- ✅ 子模块仅被测试/覆盖率选项引用（coveralls/codecov/gcov 集成）
- ❌ 子模块参与库本体构建 → 必须按 E150 拉取，不得关闭选项
- ❌ 关闭选项后把上游测试写成"跳过/不运行" → 违反双口径台账要求

## 查重关系

- similar_to: E150（同触发，不同侧重：构建必需 vs 仅覆盖率）
