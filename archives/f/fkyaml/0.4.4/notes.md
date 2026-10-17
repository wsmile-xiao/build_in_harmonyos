# fkyaml 0.4.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (clang 15.0.4, /data/service/hnp/bin, Target: aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

header-only 库（INTERFACE target），无二进制编译；核心是 CMake 配置生成上游 install 规则与测试入口：

```bash
# 上游单元测试（doctest v2.5.3，FetchContent 本地注入规避网络）
cmake -S . -B build-local -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
      -DFK_YAML_BUILD_TEST=ON -DCMAKE_BUILD_TYPE=Release \
      -DFETCHCONTENT_SOURCE_DIR_DOCTEST=$HOME/tmp/doctest-2.5.3
cmake --build build-local -j4
ctest --test-dir build-local -j2        # 372 项运行，369 通过

# R04: 补丁后 C++20 全量复验（374/374 通过）
cmake -S . -B build-cxx20 -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
      -DFK_YAML_BUILD_TEST=ON -DFK_YAML_TEST_TARGET_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD=20 \
      -DFETCHCONTENT_SOURCE_DIR_DOCTEST=<worktree>/verify-r04/doctest-2.5.3
cmake --build build-cxx20 -j4
./build-cxx20/tests/unit_test/fkYAMLUnitTest   # 374 passed / 0 failed

# Conan 配方验证（8 道门禁 G0-G4+L2/L4/L5）
python3 scripts/ohc-run.py conan-verify fkyaml 0.4.4
# → conan create（package_type=header-library，关闭 FK_YAML_BUILD_TEST 等上游选项）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时/HTML | codeload 走代理被拦、/tmp 只读 | 官方 tarball 直链下载至 ~/tmp（SHA-256 校验 75fa1ce3…45c4e），放入 build 目录复用 |
| 2 | doctest FetchContent git clone 超时 | tests/unit_test/CMakeLists.txt FetchContent 拉 github | 预下载 doctest v2.5.3 官方 tarball + `-DFETCHCONTENT_SOURCE_DIR_DOCTEST=` 注入（E342 fallback） |
| 3 | 上游 str_view.hpp 缺 `<ios>` 自包含（std::streamsize） | 头文件依赖间接包含 | test_package 源文件顶部先 `#include <ios>` |
| 4 | 3 个上游用例失败（tmpfile） | /tmp 只读 → `std::tmpfile()` 返回 NULL (errno=13) | R04 修复: 上游测试 4 处 `std::tmpfile()` 改为可写测试目录显式 `std::fopen(...,"w+b")`（补丁 `patches/0001-test-input-adapter-writable-test-dir.patch`，由配方 conandata patches 自动应用），原断言逐项保留；C++20 全量 374/374 通过 |
| 5 | 零提交新库分支 W3/JC full 模式误报 | junk_check 无 pr.diff 且 diff 为空时回退 full 全仓扫描，命中 main 历史遗留其他库垃圾文件 | 本地先行 commit 使 diff 非空 → JC 走 incremental（9 文件），不动其他库/基线 |

## 源码修改

无补丁（header-only 库零源码改动；patches/ 为空）。test_package 新增消费端测试：
- `test_package.cpp` — 消费者真实 API 消费（deserialize/迭代/序列化/异常）
- `ohos_specific_test.cpp` — HarmonyOS 专项（UTF-8 中文键值/BOM/块标量/重复键异常/std::map 语义）

## 依赖版本

- doctest v2.5.3（仅测试框架，本地注入；非运行时依赖）
- 生产依赖: 无（header-only，零 requires）

## 验证结果

```bash
# 上游单元测试（实际运行 372 项）
ctest --test-dir build-local -j2   # 369 passed / 3 env-hard-blocked / 2 C++20-gated
# Conan 配方
conan create archives/f/fkyaml/0.4.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 消费者 + 鸿蒙专项（test() 实际执行）
./test_package        # fkYAML API consumption OK
./ohos_specific_test  # HarmonyOS-specific test PASSED
```

全量通过率: 369/374 = 98.66%（含 3 项 /tmp 只读环境硬阻塞 + 2 项 char8_t C++20 门控；实际执行口径 369/372 = 99.19%）。详见 reports/upstream-test-ledger.md。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | package_type=header-library，CMakeToolchain 关闭上游测试/示例/工具，cmake_file_name=fkYAML / cmake_target_name=fkYAML::fkYAML |
| conandata.yml | 官方 GitHub tag URL + SHA-256（R39） |
| test_package/ | CMakeDeps 消费者 + test_package.cpp + ohos_specific_test.cpp + MANIFEST.yml |
| reports/upstream-test-ledger.md | 上游测试全量枚举台账（374 用例逐项分类） |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 四范围查重 + 路径决定（A） |

## 注意事项

- fkyaml 为 header-only INTERFACE 库：`cpp_info.libs=[]` 是正确写法，非缺失
- 上游测试 3 项（file_input_adapter tmpfile 系）依赖 /tmp 可写，本执行环境 /tmp 只读导致失败；CI clean 环境应可过
- char8_t 用例需 C++20 工具链（FK_YAML_HAS_CHAR8_T 门控）
- 测试框架 doctest 走 FetchContent，本地构建须注入 FETCHCONTENT_SOURCE_DIR_DOCTEST（网络不可达时）
- 路径决定: A（常规适配，依赖项身份）；C1-C3 候选均命中既有知识（E321/E322/E342/DRAFT），无新增草稿
