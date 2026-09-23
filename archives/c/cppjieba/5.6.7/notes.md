# cppjieba 5.6.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-10
- 编译器: clang/clang++
- 状态: built（首轮工作树，真机预检待 HMBS 后台执行）
- 特殊说明: header-only 库（INTERFACE target），附 dict 数据文件

## 库简介

CppJieba 是"结巴(Jieba)"中文分词的 C++ 版本。
- 上游仓库: https://github.com/yanyiwu/cppjieba
- 许可证: MIT
- 类型: header-only（`add_library(cppjieba INTERFACE)`），头文件即源码
- 词典数据: `dict/`（jieba.dict.utf8、hmm_model.utf8、user.dict.utf8、idf.utf8、stop_words.utf8）

## 官方来源核验

- 官方仓库: https://github.com/yanyiwu/cppjieba
- 正式 tag: v5.6.7
- tag commit: b3602bef7d1f67521a61788a74fb5801a0e62cd3
- 源码包: https://github.com/yanyiwu/cppjieba/archive/refs/tags/v5.6.7.tar.gz
- SHA-256: 08322f7c2a06a88e52eb0fdbc286ec86a85abae5b2a33b1e1430dba50b71960e（本机 PowerShell 下载实测，7,767,486 字节）
- 子模块: deps/limonp 为 gitlink（9d74077dfcdf8073536c97a00bb79d7a3c3fdaba），GitHub codeload tarball 仅含空目录，不含内容
- limonp 源码包: https://github.com/yanyiwu/limonp/archive/9d74077dfcdf8073536c97a00bb79d7a3c3fdaba.tar.gz
- limonp SHA-256: 2fff67ade507900ab7acb3c630b7b91232ff882f1b6240990875056befaa731b（本机 PowerShell 下载实测，18,966 字节）

## 上游测试清点（源码审计）

- 目录: test/unittest/*.cpp（gtest，FetchContent googletest release-1.12.1）+ test/load_test.cpp
- TEST 宏共 36 个（已逐文件清点，不含 gtest_main 的 InitGoogleTest）：
  - jieba_test.cpp 4、segments_test.cpp 14、trie_test.cpp 7、keyword_extractor_test.cpp 2、
    textrank_test.cpp 2、pos_tagger_test.cpp 2、unicode_test.cpp 3、unicode_path_test.cpp 1、
    pre_filter_test.cpp 1
- ctest 注册 2 项：`./test/test.run` + `./load_test`
- load_test 用 test/testdata/synthetic_doc.utf8（项目自有合成文本，无版权风险）做 50 轮 MixSegment 回归
- 证伪预案（真机轮执行）：① 确认参照 dict 非空；② ctest 日志含 `[  PASSED  ]`；③ 必要时以 exit 1 桩替换二进制确认 harness 能抓失败

## Conan 配方说明

### 配方结构
- `conanfile.py`: CMake header-library，dual-source（cppjieba + limonp）
- `conandata.yml`: 官方源码 URL + SHA256（双 source），patches 空
- `test_package/`: 消费者测试（MixSegment/Jieba/KeywordExtractor 三组真实分词断言）

### 关键配置
- `package_type = "header-library"` + `package_id: info.clear()`：纯头文件，所有配置同一包内容
- `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR`: 规避 E092（CMake 不识别 OHOS）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`：兼容新版 CMake 对 3.10 floor 的策略检查
- `CPPJIEBA_TOP_LEVEL_PROJECT=True`：确保上游测试目录被构建
- `source()`: 主包 strip_root 到 source_folder；limonp strip_root 到 `deps/limonp`（还原上游 submodule 布局，供 `LIMONP_INCLUDE_DIR` 默认分支使用）
- `build()`: configure + build + `ctest --output-on-failure`（日志留痕）+ subprocess 重跑解析并输出 `HMBS_UPSTREAM_TEST_RESULT`
- `package()`: `cmake.install()`（头文件 + dict 到 share/cppjieba/dict）+ 补装 limonp 头文件到 include/limonp（上游 install 遗漏但公头依赖）+ LICENSE + res/upstream_test_result.json
- `package_info()`: `cmake_file_name=cppjieba`、`cmake_target_name=cppjieba::cppjieba`、`libs=[]`、`resdirs=["share"]`

### 平台适配
- R32: `self.settings.os in ("Linux", "OHOS")`
- 无 patches，无 `__OHOS__` 宏，纯 POSIX/C++11 代码，无平台分支需求

## 依赖

无必需依赖。limonp 随包（submodule 双 source，非 conan requires）。上游测试的 googletest 由 CMake FetchContent 在构建时获取（真机需外网 GitHub 可达；若不可达则按 HMBS 诊断处理）。

## 测试说明

### 上游测试
- 命令: `ctest --output-on-failure`（build 文件夹）
- 期望: 2/2 通过（test.run 内 36 gtest + load_test 回归）
- 标记: `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed/failed/skipped 来自 ctest 输出解析）

### test_package 测试
- 文件: `test_package/test.cpp`（3 组）
  1. MixSegment 精确分词"他来到了网易杭研大厦"→"他/来到/了/网易/杭研/大厦"
  2. Jieba 用户词"男默女泪"插入前后 + CutForSearch
  3. KeywordExtractor Top5 含 CEO 且权重非零
- 词典路径: 由 test_package conanfile 从包内 `share/cppjieba/dict` 经 `CPPJIEBA_DICT_DIR` 传入
- 标记: `HMBS_TEST_PACKAGE_RESULT`（discovered=3，passedCount 来自 `[PASS]` 计数）

## 验证结果

首轮仅完成工作树（按任务要求不 commit、不 push、不建 PR）。待 HMBS 后台真机预检（conan create + test_package + ctest）返回 evidence 后回填通过率。

## 注意事项

1. **Header-only + 数据文件**：无 .a/.so，无 ELF 签名/RPATH 需求；dict 随包在 share/cppjieba/dict
2. **limonp 必须随包**：公头 `#include "limonp/*.hpp"`，上游 install 不装 limonp，配方已补装
3. **C++ 标准**：上游默认 C++11，profile 给 C++17，兼容
4. **googletest 外网依赖**：上游测试构建时 FetchContent 克隆 googletest，若真机外网受限会导致上游测试失败，届时按 HMBS 诊断改用 vendored 方案
