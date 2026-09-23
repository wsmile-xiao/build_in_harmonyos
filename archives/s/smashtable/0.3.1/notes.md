# smashtable 0.3.1 适配笔记

## 编译环境
- 构建系统: CMake ≥ 3.21（header-only INTERFACE 目标 + 测试/示例）
- 编译日期: 2026-09-05
- 编译器: OHOS clang 15.0.4（libc++），cmake 4.1.2
- 状态: built（conan-verify 通过；published 需合并后 release/upload 流水线确认）

## 编译步骤

1. `cmake -B build -DCMAKE_BUILD_TYPE=Release -DSMASHTABLE_BUILD_CUDA=OFF`（上游 CMakePresets 同款，关掉仅在有 nvcc 时启用的 CUDA 测试腿）
2. `cmake --build build -j4` —— 9 个测试二进制 + example 全部编译
3. `ctest --test-dir build --output-on-failure` —— 9/9 套件通过（2.49 s）
4. `conan create` 走配方复现同一路径（W3）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: no template named 'atomic_ref' in namespace 'std'`（shared.hpp:1324） | OHOS clang 15 libc++ 未实现 C++20 `std::atomic_ref`（libc++ 16 才有） | 0001 补丁：`__cpp_lib_atomic_ref` 特性宏守卫，缺失时用 `__atomic_load_n/store_n/fetch_or/xor/add/sub` 内建实现最小 `atomic_ref`（含 `store`、轮询式 `wait` + `std::this_thread::yield`、空 `notify_all`），仅覆盖库用到的整型原子操作面 |
| 2 | `error: expected a type`（basic_avl_tree.hpp:1147 `allocator_traits<A>::template rebind_alloc`） | C++20 P0634 允许省略 `typename`，clang 16 才实现该放宽；上游 CI 用 clang 17+ | 0002 补丁：显式补 `typename`，新旧编译器均合法 |
| 3 | `error: no template named 'format_string' in namespace 'std'`（scripts/test.hpp:314） | OHOS libc++ 的 `<format>` 头存在但是空壳：`std::vformat`/`make_format_args`/`format_string` 全部缺失 | 0003 补丁：`__cpp_lib_format` 守卫；缺失时 `print_line` 改为 `ostringstream` 最小格式化，支持测试框架状态行用到的 `{}` 与 `{:.2f}`；有完整 `<format>` 的环境仍走 `std::format` |

## 源码修改

三个补丁（`patches/`，全部为可移植性修改，无平台宏）：

- `0001-shared-atomic-ref-fallback.patch`：`include/smashtable/shared.hpp`，非 CUDA 分支按特性宏 fallback；调用点语义不变（fetch_or/xor/add/sub、load/store、wait、notify_all）
- `0002-avl-tree-allocator-typename.patch`：`include/smashtable/basic_avl_tree.hpp`，一个词的修正
- `0003-test-format-fallback.patch`：`scripts/test.hpp`，测试框架输出函数

## 依赖版本

无第三方依赖（纯 C++20 标准库）。

## 验证结果

```bash
ctest --output-on-failure   # 100% tests passed, 0 tests failed out of 9
# 运行时用例 548 个全部 ok，0 skipped
```

## 注意事项

- 语言预检误报说明：上游带可选 Python 绑定（pyproject.toml/setup.py + python/ 目录，
  裸 CPython C-API C++ 扩展），`lang-preflight` 判为 mixed 并写 env_unsupported。
  按 R47 附录 D.4-2 绑定包口径，绑定包按源码主体判 cpp（cpp 源 35 个文件、
  CMake 构建系统、任务语言 cpp），本次判定为检测器误报，保留证据继续适配。
  Python 绑定 wheel 不在 Conan 适配范围。
- 上游 tag 为 `v0.3.1`（带 v 前缀），archive URL 无 `.tar.gz` 后缀由 Conan `get()`
  正常处理 GitHub archive 重定向。
- 上游无 LICENSE 文件（pyproject.toml 标注 Apache-2.0），配方 license 字段取
  Apache-2.0，package() 不拷贝许可证文件。
- `SMASHTABLE_BUILD_CUDA=OFF` 是显式声明而非环境探测：设备与 CI 均无 nvcc，
  上游 `check_language(CUDA)` 找不到编译器时本就不会注册该测试，显式关闭保证
  本地与 CI 注册面一致（9 个套件）。
- `wait()` fallback 是轮询 + yield，无 futex 睡眠语义；库只把 waiting 用于就绪
  等待，语义可接受，已在补丁注释中说明适用边界。
## 路径 B 知识贡献（用户已确认）

- 知识草稿：`knowledge/drafts/DRAFT-libcxx15-missing-cpp20-atomic-ref.kv` + `.md`（draft-review 质量预检三项全过；与库内 E196 相似度 0.36 属灰区不同问题，正式库无 atomic_ref 条目）
- 知识库扩展 Issue：#2702（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2702），PR 创建后回填编号并保持双向关联
- 同家族缺口（format stub / P0634 typename）已有 DRAFT-ohos-libcxx15-format-ranges-capability-gap 与 E397 覆盖，本次不重复沉淀
---

**编译结束**: 2026-09-05 20:59
**最终状态**: built
