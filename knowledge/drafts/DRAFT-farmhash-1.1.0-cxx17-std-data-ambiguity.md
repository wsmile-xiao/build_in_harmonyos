# DRAFT: C++17 + libc++ 下 `using namespace std;` 与全局 `data` 标识符歧义（farmhash 1.1.0 确认实例）

> **状态**: 草稿（未审核、未合入正式知识库）
> **查重**: knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations 四范围均未命中
> `std::data` / `reference to 'data' is ambiguous` 错误模式（E293 仅覆盖 C++17 移除
> throw()/register 的告警升级，E130/E455/E538 仅覆盖 libc++ 链接/标准库路径问题）。
> 本稿为新增知识候选，待 promote 审核。

## 问题签名

- 错误日志：`farmhash.cc:2002:14: error: reference to 'data' is ambiguous`（共 20 errors）
- 触发工具/阶段：conan create 内 `make`（AutotoolsToolchain 注入 `-std=c++17 -stdlib=libc++`）
- 匹配 signature：`reference to 'data' is ambiguous|candidate found by name lookup is 'data'|candidate found by name lookup is 'std::data'`

## 根因

旧 C++ 源码（farmhash 2015 v1.1）在文件顶层有 `using namespace std;`（farmhash.cc:405），并在多个
自测命名空间（farmhashcc / farmhashmk / farmhashna / ... 共 9 处）声明全局数组
`static char data[kDataSize];`。C++17 在 `<iterator>` 中新增 `std::data` 函数模板；当工具链
注入 `-std=c++17 -stdlib=libc++` 时，未限定的 `data` 在数组变量与 std::data 模板之间产生
名字查找歧义。**C++14 默认构建不触发**（std::data 不存在），因此本地手工 make 常绿而
conan create（profile cppstd=17）红——双构建环境不一致的典型来源。

## 本库真实证据（farmhash 1.1.0, google/farmhash）

| 项目 | 值 |
|------|-----|
| 官方仓库 | https://github.com/google/farmhash |
| 官方提交 | `34c13ddfab0e35422f4c3979f360635a8c050260`（v1.1, 2015-03-01） |
| 归档 SHA-256 | `9fb93e0b8881ef96a9f81f9096315eaf3cd727b58d7e2e569ac1208a2a81e76e` |
| 冲突点 | farmhash.cc `using namespace std;` + 9 处 `static char data[kDataSize];` + 100 处 `data` 引用 |
| 本地构建 | `clang++`（默认标准）make + check → 1/1 PASS |
| conan create | `-std=c++17 -stdlib=libc++` → 20 errors（data 歧义） |
| 修复后 | 改名 `data`→`farmhash_data`（0003-src-farmhash.cc.patch），make/check 1/1 PASS、conan create + test_package 全过 |

### 现象复现（修复前）

```bash
cd $WORKTREE/archives/f/farmhash/1.1.0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
# → farmhash.cc:2002:14: error: reference to 'data' is ambiguous (20 errors)
```

## 修复

在自测区把 `static char data[kDataSize];` 及全部引用改名为 `farmhash_data`（`data-parallel`
等注释保留），不改变公共头文件 `farmhash.h` 与 ABI。patch 见
`archives/f/farmhash/1.1.0/patches/0003-src-farmhash.cc.patch`。

## 适用边界 / 反例

- 适用：所有 `using namespace std;` + 全局/命名空间级 `data`（或其他 C++17 新增 std 同名
  标识符 begin/end/empty/size）的旧 C++ 库，在 cppstd=17 工具链下编译。
- 反例/不适用：无 `using namespace std;` 的源码；只在使用处局部限定的代码；C++14 工具链
  （不触发，但建议仍改名为未来兼容）。
- 备选方案：conanfile.py `generate()` 追加 `-std=c++14`（fallback），或移除 using 指令
  （改动面大），或 `-fpermissive`（禁止，掩盖歧义导致语义不确定）。

## 查重差异（新增部分 vs 既有条目）

- E293（C++17 移除 throw()/register）仅覆盖「特性移除→告警升级」，不覆盖「using 指令 +
  全局标识符 vs std 模板 名字查找歧义」。
- E130/E455/E538 覆盖 libc++ 链接路径/标准库问题，与本命名歧义无重叠。
- 新增差异：C++17 新 std 模板与用户全局标识符的歧义模式 + 改名修复 + 双环境（本地 C++14
  绿 / CI cppstd=17 红）判别特征。

## 关系字段

- similar_to: E293, E130
- caused_by / causes / conflicts_with / prerequisite_of: 无
