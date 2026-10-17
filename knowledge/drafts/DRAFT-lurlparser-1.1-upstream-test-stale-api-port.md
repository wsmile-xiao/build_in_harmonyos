# DRAFT-lurlparser-1.1-upstream-test-stale-api-port：上游 tag 内测试引用与同 tag 头文件不一致的已移除旧 API（clParseURL/m_* -> ParseURL/scheme_*），需以最小补丁移植测试到当前公开 API 后真实运行

> Contributor: oh-executor-pc4-34 | Status: Draft | Updated: 2026-09-22
> Source: lurlparser 1.1 适配（PR feat/lurlparser-1.1）；触发场景：上游 test/ 目录与 release-1.1 头文件 API 不同步
> 对应：`knowledge/drafts/DRAFT-lurlparser-1.1-upstream-test-stale-api-port.kv`

## 现象

上游 tag `release-1.1` 内 `test/test.cpp` 引用了一组**同 tag 头文件已不存在**的旧 API：

```cpp
// test/test.cpp（tag 原样）
using LUrlParser::clParseURL;
clParseURL URL = clParseURL::ParseURL( "https://John:Dow@github.com:80/..." );
URL.IsValid(); URL.m_Scheme; URL.m_Host; URL.m_Port; URL.m_Path; URL.m_Query;
```

而 release-1.1 的 `LUrlParser.h` 提供的是重命名后的公共 API：

```cpp
namespace LUrlParser { class ParseURL { ... std::string scheme_, host_, port_,
  path_, query_, fragment_, userName_, password_; bool isValid() const;
  static ParseURL parseURL(const std::string& url); }; }
```

`make tests`（`gcc -o tests test.cpp ../LUrlParser.cpp -std=c++11 -lgtest`）直接编译失败：

```text
error: 'clParseURL' was not declared in this scope
error: no member named 'm_Scheme' in 'LUrlParser::ParseURL'
```

这是**上游自身的一致性缺陷（stale test）**：类/成员重命名后测试目录未同步。
不是平台问题，也不是"上游没有测试"——8 个活跃 `TEST_F` 用例真实存在于 tag 源码。

## 双口径台账（本库实证）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 8 | test/test.cpp 中 8 个活跃 TEST_F（example/cases/ipv6/ipv4/parens/trailingdot/specialchars/escapechars） |
| configured_executable_total | 8 | 补丁 0002 移植后经 WITH_TESTS 接入 CMake 目标 lurlparser_tests（1 二进制，注册 8 用例） |
| executed_passed_total | 8 | ctest -R lurlparser_tests 实际运行 8/8 PASSED |
| 注释保留 | controlchars | 上游 `/* ... */` 注释，不计入活跃声明，台账中列出 |

通过率（全量分母）：`8/8 = 100%`；逐用例输出见 `upstream-tests.log`
（SHA-256: 2d8b7a7987d5b010d9aa9c22f5f0ffd2550f2f52126ec8207bd40aeb252eef69）。

## 根因

版本演进中公共 API 重命名（类 `clParseURL`→`ParseURL`；成员 `m_*`→`*_`；
`IsValid`→`isValid`；静态工厂 `ParseURL(...)`→`parseURL(...)`），tag 内
测试目录未同步更新。编译期首个错误即 `clParseURL not declared`。

## 方案（最小补丁移植 + 真实运行）

1. **定性**：原样编译记录首错，证明"测试存在但不可编译"而非"没有测试"。
2. **最小补丁**：仅把 test/test.cpp 的 API 调用逐字映射到当前公开头，
   保持断言语义不变（`patches/0002-test-test.cpp.patch`）；
   `conandata.yml` 声明补丁，`WITH_TESTS=ON` 时经 CMakeDeps 接入
   `gtest/1.17.0`（制品仓已发布）。
3. **真实运行**：conan create（ohos-aarch64 profile, with_tests=True）rc=0，
   上游 8/8 PASSED；消费者与 OHOS 专项测试均 PASSED；
   如实回填双口径通过率 `8/8 (100%)`。

## 适用边界 / 反例

- 适用：release tag 内 test 与头文件 API 不同步的小型 C++ 库
  （类/成员重命名、命名空间迁移、静态工厂改名、enum 改名）。
- 不适用：测试因真实外部依赖/平台缺失而失败的情况（走 E365/E332 等条目）；
  仅凭标题/库名相似不算重叠。
- 反例：上游测试确实引用当前 API 但仍编译失败 → 属编译错误修复，非本模式。

## 查重差异（七轴摘要）

- exact_duplicate: 无（knowledge 库无 lurlparser/URL 解析旧 API 条目）
- causal_duplicate: 无（E365 为 MPICH abort 测试 oracle，根因不同）
- trigger_overlap: 部分——同属"上游测试无法运行"，但触发面是 API 移除非框架缺失
- solution_overlap: 无——E332 是 GTest 发现/CTest 迁移，本条目是测试 API 最小移植
- combination_novelty: 有（"API 重命名后测试不同步 → 最小补丁移植 → 双口径回填"组合新）
- boundary_novelty: 有（明确"不可编译≠失败≠没有测试"的判定边界）
- test_migration_novelty: 有（逐字映射移植保持断言语义，8/8 实证）

relationships:
  similar_to: [E365]
  caused_by: []
  prerequisite_of: []
  conflicts_with: []