# openddl-parser 0.5.1 适配笔记

## 编译环境
- 构建系统: cmake（上游根 `CMakeLists.txt`，min 3.8）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（HarmonyOS PC aarch64，C++17 / libc++）
- 状态: built

## 编译步骤

源码：官方 GitHub tag 归档 `https://github.com/kimkulling/openddl-parser/archive/refs/tags/v0.5.1.tar.gz`
（sha256 `511146377636f56a8a3bd6daace5ac2ed9672f4be28fc2c90597f4e88e069ffc`，与 conan-center-index 同版本 conandata 逐字一致）。

```bash
# 1) 上游原生基线（沙箱 HOME，供上游测试表取数）
cmake -G Ninja -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
      -DDDL_BUILD_TESTS=ON -DDDL_BUILD_PARSER_DEMO=ON
cmake --build <build> -j4
<build>/bin/openddlparser_unittest          # 125 tests / 10 test cases, PASSED 125

# 2) Conan 配方（profile: ci/conan/profiles/ohos-aarch64）
conan create . -pr:h=<profile> -pr:b=<profile>
#   generate(): DDL_STATIC_LIBRARY=ON / DDL_BUILD_SHARED_LIBS=OFF /
#               DDL_BUILD_TESTS=ON / DDL_BUILD_PARSER_DEMO=OFF
#   build():    cmake.configure + cmake.build + bin/openddlparser_unittest（上游测试）
#   package():  cmake.install + 拷 LICENSE + 删除 lib/cmake（交由 CMakeDeps 接管）
#   test():     self.run(test_package 二进制) — 9 条消费者断言
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化时把构建系统判成 autotools 并生成 autotools 配方骨架 | `init-build` 按下载 URL 形态猜 `BUILD_SYSTEM`，GitHub tag 归档 URL 无 autotools/cmake 特征 | 按上游根 `CMakeLists.txt` 实测改写为 CMake 配方（`CMakeToolchain` + `CMake`） |
| 2 | 下载 URL 搜索给出 4 个 Savannah/waterlan 地址，实测全部 404 | 搜索器按 HEAD 响应判定可用，镜像站对不存在的路径返回 404 仍算“可达” | 显式指定官方 GitHub tag 归档 URL，实测下载与 sha256 双 URL 形态一致 |
| 3 | `OpenDDLParser::getVersion()` 返回 `"0.4.0"`，与 tag v0.5.1 不一致 | 上游 `code/OpenDDLParser.cpp` 的 `Version` 字面量自 0.4.0 后未随 tag 更新（上游遗留，非适配缺陷） | 消费者测试只断言“非空版本串”并打印实测值，不把 0.5.1 硬断言进测试；在本笔记与测试台账留痕 |
| 4 | 初始 test_package 是 `printf` C 空壳 | 生成模板默认按 C 项目产出，未链接被测库 | 重写为 C++ 消费者：经 `openddlparser::openddlparser` 目标链接，覆盖版本接口/合法解析/根节点树结构/垃圾输入拒绝 9 条断言 |
| 5 | 上游测试二进制在 conan 构建期需要 `OPENDDL_TEST_DATA` 指向源码夹具 | 上游以 `OPENDDL_TEST_DATA="${PROJECT_SOURCE_DIR}/test/TestData"` 定义（CMakeLists 自带） | 保持上游定义不改，conan 构建目录里源码夹具随包同步存在，实测 125/125 通过 |
| 6 | `test_package/build/` 构建目录落在包目录内 | conan create 在 `test_package/` 原地 configure | 仓库 `.gitignore` 的 `build/` 规则覆盖该路径；提交前再清理一次，保证提交面只有配方文件 |

## 源码修改

无补丁（`patches: []`）。上游 CMake 在 HarmonyOS PC 上原样可配置、可构建、可安装，未触碰平台宏、未注入 `-D__OHOS__`、未改上游任何测试用例。

## 依赖版本

- Conan 运行时依赖：**0**（`requirements()` 为空；预检脚本实测“无依赖需要检查”）
- 测试依赖：上游自带 `contrib/gtest-1.7.0` 内嵌 gtest 源码，直接编进 `openddlparser_unittest` 目标（不引入 conan gtest 依赖）
- 系统库：Linux/FreeBSD 声明 `m`（本包实测仅用 `atof`，libc 提供）

## 验证结果

```bash
# 上游原生基线（沙箱 HOME）
<build>/bin/openddlparser_unittest
#   [==========] 125 tests from 10 test cases ran. (8 ms total)
#   [  PASSED  ] 125 tests.            → TOTAL 125 = PASS 125 + FAIL 0 + SKIP 0 + NOT_RUN 0

# Conan 配方（干净缓存轮）
conan create … ; 结果：构建 + 上游测试 125/125 + test_package 9/9 全通过
#   安装树: lib=True / bin=False / include=True（静态库包，无 bin 属预期）

# 消费者测试（test_package）
SUMMARY checks=9 passed=9 failed=0
```

计数口径（四口径分别登记，不混用）：

| 口径 | 值 | 取数命令 |
|---|---|---|
| 源码宏数（TEST/TEST_F 注册） | 125 | `grep -c -E "^\s*(TEST|TEST_F)[[:space:]]*\(" test/*.cpp` |
| 框架注册并实跑（gtest 报告） | 125（10 test cases） | 测试日志 `[==========] 125 tests from 10 test cases ran.` |
| 断言数（EXPECT_*/ASSERT_*） | 423 | `grep -h -o -E "\b(EXPECT|ASSERT)_[A-Z_]+" test/*.cpp \| wc -l` |
| 消费者断言数（test_package） | 9 | `test_package/consumer.cpp` 的 `check()` 条目 / 运行输出 `SUMMARY checks=9` |

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` + `conandata.yml` + `manifest.yaml` | Conan 配方（CMake，静态库，零补丁） |
| `test_package/{CMakeLists.txt,conanfile.py,consumer.cpp,MANIFEST.yml}` | 消费者测试 + 上游测试声明 |
| `notes.md` | 本笔记 |

## 注意事项

- 版本查询接口返回的是上游维护的 `Version` 字面量 `"0.4.0"`（上游遗留），不是适配引入的问题。
- 上游测试在配方 `build()` 内执行（`bin/openddlparser_unittest`），上游 CMake 未注册 CTest 用例，故不使用 `ctest`。
- 本包为纯库产物（`install()` 只装 lib/include/cmake 配置，不装可执行文件），因此**不建** `commands.json`。
- 知识沉淀：适配全程一次通过，未出现需知识引擎匹配的失败模式，按条件触发口径**零草稿**（正常终态）。
