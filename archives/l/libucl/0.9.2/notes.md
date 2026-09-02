# libucl 0.9.2 适配笔记

## 编译环境

- 构建系统: CMake
- 编译日期: 2026-09-01
- 编译器: clang 15.0.4
- 目标配置: OHOS armv8, Release, static library
- 状态: built

## 编译步骤

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DENABLE_UTILS=OFF \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j2
```

最终 Conan 配方使用 `CMakeToolchain`，关闭可选 Lua 和 utility binaries，并在 `CMake.configure()` 中传入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autogen.sh` 无法执行 | 构建环境未提供 `aclocal` | 使用上游已提供的 CMake 构建路径；测试仍按上游 Autotools 测试源码和脚本执行。 |
| 2 | CMake 4.1 拒绝最低版本 3.1 的项目 | CMake 已移除对低于 3.5 的兼容行为 | 配方的 `cmake.configure()` 传入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。 |
| 3 | `schema.test` 不能写入 `/tmp/_ucl_test_schema.out` | 鸿蒙环境 `/tmp` 只读 | 保留并执行原脚本，记录其失败；随后逐个向同一 `test_schema` 程序输入 25 个 JSON schema，全部成功。 |
| 4 | `streamline.test` 无法创建输出文件 | 上游 `test_streamline.c` 仅在 `argc == 2` 时读取输出路径，但脚本仅传一个参数 | 保留原脚本并记录其基线比对失败；程序标准输出与 `tests/streamline.res` 内容一致。 |

## 源码修改

无。适配只在 Conan 配方层传递 CMake 兼容参数，未修改上游源码或上游测试。

## 依赖版本

无 Conan 包依赖；默认关闭需要 OpenSSL、Lua 或 curl 的可选功能。配方声明系统数学库 `m` 为静态 `ucl` 库的消费者链接依赖。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify libucl 0.9.2
# G1/G2/G3/G4/L2/L4/L5: PASS

CI_REPO_ROOT="$PWD" JUNK_PR_DIFF="$PWD/.ohc/libucl-0.9.2.pr.diff" \
  zsh ci/conan/build_and_test.sh archives/l/libucl/0.9.2
# L0/L1/L4/L5: PASS; consumer test: 1/1 PASS
```

完整上游测试记录见 `reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libucl.a` | libucl 静态库 |
| `include/ucl.h` | C API 头文件 |
| `include/ucl++.h` | C++ API 头文件 |
| `share/ucl/ucl-config.cmake` | CMake package export |

## 注意事项

- 上游版本同时包含 Python 绑定和 C 主库；本次交付范围是 C/C++ `libucl` 库。
- 此版本 CMake 目标导出为 `ucl::ucl`，Conan 包元数据使用同一目标名。
---

**编译结束**: 2026-09-01 23:38
**最终状态**: built
