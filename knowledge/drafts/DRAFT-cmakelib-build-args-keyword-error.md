# DRAFT：Conan CMake.build() 不接受 `args=` 关键字 → 用 build_tool_args

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `conan, cmake, recipe` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-cmakelib-build-args-keyword-error.kv`
> similar_to: E426

---

**触发场景**：Conan 配方 build() 中向 `CMake.build()` 传入 `args=["-j1"]`
（沿用 autotools/Makefile 思路的直觉写法），conan create 在 build() 阶段直接报
TypeError。

## 错误签名

```text
TypeError: CMake.build() got an unexpected keyword argument 'args'
```

## 错误摘录

```text
ERROR: libcorrect/3.5@ohpcd/stable: Error in build() method
        cmake.build(args=["-j1"])
        TypeError: CMake.build() got an unexpected keyword argument 'args'
```

## 根因

Conan 2.29.1 `conan/tools/cmake/cmake.py` 的 `CMake.build()` 签名为
`build(build_type=None, target=None, cli_args=None, build_tool_args=None,
stdout=None, stderr=None, subfolder=None)`，**不存在 `args` 参数**。
- `build_tool_args`：传给底层构建工具（make/ninja），拼在 `cmake --build ... --` 之后；
- `cli_args`：直接传给 `cmake --build ...` 的参数。

向 make 传 `-j1`（OHOS SELinux 禁 make jobserver FIFO，E074）必须用 `build_tool_args`。

## 推荐方案（rec_approach: `cmake-build-build-tool-args`）

```python
cmake.build(build_tool_args=["-j1"])   # 而不是 cmake.build(args=["-j1"])
```

已验证：libcorrect 3.5 conan-verify G2 修复前 FAIL（上述 TypeError）、修复后 PASS，
W3 本地 CI 模拟（setup.sh + build_and_test.sh）构建/测试通过。

## 与既有条目差异（七轴）

- E426（pico-sdk）rec_command 出现 `build_tool_args=["-j1"]`，但那是"正确用法"，
  未记录 `args=` 关键字不存在的错误面；DRAFT-zmusic 记录的是 build_tool_args 带 `--`
  的坑（make 把 `-jN` 当目标名），与本错误面互补不重叠。
- 本条目捕捉"从 args= 迁移到 build_tool_args"的 API 契约错误面，查重未命中。

## 适用边界

- 所有 Conan 2.x CMake 配方 build() 需要向构建工具传参（-j1、-jN 等）的场景；可跨库复用。
- 非边界：cli_args 场景（直接传 cmake --build 参数）属另一参数，不受影响。

## 关系

similar_to: E426；`prerequisite_of` 无；`conflicts_with` 无。

---
*本文件由 `knowledge/drafts/DRAFT-cmakelib-build-args-keyword-error.kv` 派生；与 libcorrect 归档同 PR 交付，待主编审核 promote 后转入 doc/。*