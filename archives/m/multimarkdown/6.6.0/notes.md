# MultiMarkdown 6.6.0 适配笔记

## 软件信息

- 上游: https://github.com/fletcher/MultiMarkdown-6
- 版本: 6.6.0
- 许可证: MIT
- 构建系统: CMake
- 产物: `multimarkdown` CLI、便捷脚本、`libMultiMarkdown.a`、公共头文件

## 适配要点

- 使用官方 GitHub codeload tag tarball: `https://codeload.github.com/fletcher/MultiMarkdown-6/tar.gz/refs/tags/6.6.0`
- CMake 工程声明 `cmake_minimum_required(VERSION 2.6)`，在 CMake 4.x 下需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- OHOS profile 会映射到 HarmonyOS，当前上游 CMake 只在 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 分支启用 Linux 打包/安装逻辑，因此配方在 OHOS/Linux 下设置 `CMAKE_SYSTEM_NAME=Linux`。
- 设置 `SHAREDBUILD=ON` 让上游安装静态库与公共头文件，便于 Conan 消费者链接测试。
- profile 中编译器路径可能指向不存在的 `/data/service/hnp/bin/clang*`，配方生成后替换为 PATH 中的 `clang`/`clang++`。

## 测试说明

上游 6.6.0 release tarball 包含完整的测试套件：

1. **CuTest 单元测试**：`test/CuTest.c` / `test/CuTest.h`，通过 `make-tests.sh` 自动扫描 `src/*.c` 中的测试函数，编译为 `run_tests` 可执行文件，通过 ctest 执行。
2. **Perl 集成测试**：`tests/MarkdownTest.pl` 驱动，`tests/MMD6Tests/` 提供 60+ 测试数据（Abbreviations、Tables、Math、Metadata 等），CMakeLists.txt 通过 `ADD_MMD_TEST` 宏注册 11 个 ctest 用例（mmd-6、mmd-6-compat、mmd-6-latex、mmd-6-beamer、mmd-6-memoir、mmd-6-fodt、mmd-6-opml、mmd-6-critic-accept、mmd-6-critic-reject、pathologic-compat、pathologic）。

`conanfile.py` 的 `build()` 中已集成 `self.run("ctest --output-on-failure --parallel 1")` 执行上游测试，使用 `can_run(self)` 保护交叉编译场景。
注意：ctest 已移除 `|| true`，让测试失败真实暴露。CMake 配置中传递 `-DTEST=ON` 以启用 CuTest `run_tests` 单元测试（通过 patch 0001 将上游 `add_definitions(-DTEST)` 改为 `target_compile_definitions(run_tests PRIVATE TEST)`，避免泄漏到 `multimarkdown` CLI 目标），确保全部 12 个 ctest 用例（1 个 CuTest + 11 个 ADD_MMD_TEST）被注册和执行。

本次 test_package 另做了两类实质验证：

1. C 消费者链接 `libMultiMarkdown.a`，包含 `libMultiMarkdown.h`，调用 `mmd_string_convert("*hi*\\n", ...)` 并断言输出包含 `<em>hi</em>`。
2. 执行打包后的 `bin/multimarkdown`，验证 Markdown 到 HTML 转换和 `--version`。

## 验证命令

```bash
python3 -m py_compile archives/m/multimarkdown/6.6.0/conanfile.py archives/m/multimarkdown/6.6.0/test_package/conanfile.py
conan create archives/m/multimarkdown/6.6.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
python3 scripts/ohc-run.py finish multimarkdown 6.6.0 built
```

## 知识图谱

未生成新知识草稿；CMake 版本兼容与上游测试执行已在 notes 与 MANIFEST 中记录。
---

**编译结束**: 2026-07-22 17:13
**最终状态**: built
