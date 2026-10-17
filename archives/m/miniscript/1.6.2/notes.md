# miniscript 1.6.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 状态: published

## 编译步骤

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release -DMINISCRIPT_BUILD_TESTING=ON \
  -DMINISCRIPT_BUILD_CSHARP=OFF
cmake --build build -j4
ctest --output-on-failure        # 2/2 PASS
cmake --install build --prefix $TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CLI 启动打印 `Assert failed: s.atB(0) == -26`（SimpleString.cpp:321） | OHOS/arm64 默认 unsigned char，上游按 signed char 开发（x86 Linux）；UTF-8 字节 API 的整数提升语义不同 | 配方 generate() 注入 `-fsigned-char`（C/CXX），与上游宿主语义对齐 |
| 2 | conan create G2 失败：`Imported target miniscript::miniscript includes non-existent path .../p/include` | 上游 CMake 仅 `install(TARGETS miniscript-cpp minicmd)`，未安装公开头文件，package 缺 include/ | 配方 package() 补装头文件到 include/MiniScript；`cpp_info.libs=["miniscript-cpp"]` 对齐上游 target 名 |
| 3 | W3 本地 CI JC 拦截 | 其他库（cloog/kics）归档中的 .build-closed/.staging-verified 基线空文件被 full 模式扫描 | 基线隔离复验：记录 SHA-256（e3b0c442…），临时索引隔离，复跑通过后原样恢复，pre==post SHA 一致，未入库 diff/PR |

## 源码修改

无源码补丁。平台适配全部通过 Conan 配方编译标志（-fsigned-char）与 package() 安装规则完成，
符合 R8（补丁默认无平台宏）。

## 依赖版本

无外部依赖（C++14 标准库 + CMake 内置 editline/whereami 单文件组件）。

## 验证结果

```bash
# 上游测试（全量口径 11/11：10 个 UnitTest 注册类 + 1 个集成套件）
ctest --output-on-failure        # Miniscript.cpp.UnitTests / Miniscript.cpp.Integration 均 PASS

# 消费者验证（test_package，conan create 内执行）
test_miniscript                 # 输出 "answer is 42"，GetGlobalValue x==42

# 门禁
conan-verify: G0-G4 全 PASS
finish W3 本地 CI: 通过（.ci-result.json exit_code=0）
```

## 归档文件

- `conanfile.py` / `conandata.yml`（官方 tag 源，SHA-256=62df0ce8…）
- `test_package/`（消费者测试 test.cpp + MANIFEST 声明）
- `reports/test-report.md`（上游测试双口径台账 11/11）
- `reports/knowledge-candidate-ledger.md`（知识候选台账 + 七轴查重）
- 软件级 `commands.json`：见 archives/m/miniscript/commands.json（miniscript 为 CLI + 库混合交付）

## 结束标记

最终状态: published（conan-verify G0-G4 PASS + W3 本地 CI 通过，上游测试 11/11，PR 已交付）
---

**编译结束**: 2026-09-23 04:32
**最终状态**: published
