# DRAFT-chaiscript-6.1.0-cross-dso-typeinfo-identity：OHOS 跨 dlopen 边界 type_info 同一性不成立

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: chaiscript 6.1.0 HarmonyOS PC 适配（PR #8935，上游套件真机 417/429 中 12 个失败的定性）
> 对应：knowledge/drafts/DRAFT-chaiscript-6.1.0-cross-dso-typeinfo-identity.kv

## 现象

真机全量执行上游测试套件，12/429 失败高度聚集：11 个 `.chai` 用例全部调用
`load_module()`，外加 multithreaded_test。报错形态全是**类型分派失败**而非
加载失败：

```text
Error: "Error with function dispatch for function 'to_string'" With Parameters: (const int)
Error: "Error with function dispatch for function 'push_back_ref'" With Parameters: (List).(int)
Error: "Can not find appropriate '==' operator." With Parameters: (const string, NSt4__n112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEE)
```

补建上游 `chaiscript_stdlib-6.1.0` 模块复测 multithreaded_test：dlopen 成功、
模块注册成功，仍报 `to_string(const int)` 分派失败——排除"缺模块"假因。

## 根因（探针实证）

40 行最小探针：exe 与 dlopen 的 .so 各自提供同一类型的 `typeid`，对比指针、
`operator==`、名字：

```text
which=0 exe=0x55c01c5008 mod=0x5acf502d58 ptr_same=NO op_eq=NO exe_name=NSt4__n14listIiNS_9allocatorIiEEEE mod_name=NSt4__n14listIiNS_9allocatorIiEEEE
which=2 …（std::string，同样 ptr_same=NO op_eq=NO，名字逐字符相同）
```

- **类型名完全相同，`std::type_info::operator==` 仍返回 false**。glibc/libstdc++
  （及主流 libc++abi）的 `__class_type_info::operator==` 有名字字符串回退，跨
  DSO 模板实例化也能判等；OHOS 的 libc++_shared.so 没有这条回退（或对
  dlopen 场景不生效）。
- 双方都已 `NEEDED libc++_shared.so` **也救不了**：共享库只合并其自身导出的
  type_info 符号，模板在用户代码里的实例化各 DSO 一份；连 std::string
  （显式实例化）也失败，说明回退机制整体缺失。
- chaiscript 的 `Type_Info::operator==`（dispatchkit/type_info.hpp）仅
  `指针相等 || *ti == *m_type_info`，无自有名字回退 → 模块注册的函数签名
  与主程序对象分派必失败。

## 方案

1. **交付/使用形态**：伞形头 `ChaiScript()` 默认构造（编译内置
   `Std_Lib::library()`，零 dlopen）——上游推荐形态，header-library 交付的
   自然用法。此形态下 363 非模块 .chai + 48 Catch + 6 独立程序 + test_package
   8 断言全过。
2. **定性流程**：遇到跨模块类型分派失败，先跑探针区分"平台限制 vs 配方缺陷"，
   再写进 PR 已知限制；不要盲目改配方或补模块。
3. 需要模块生态的使用者：接受限制，或推动上游按类型名字符串分派（超出
   适配范围）。

## 验证（真实证据）

- 探针输出如上（三类类型全覆盖，含用户模板与 std::string）
- multithreaded_test 两轮：缺模块 → abort；补建模块 → dlopen/注册成功但
  分派失败（同根因确认）
- 上游套件 417/429，12 失败与 `load_module`/模块型构造 100% 相关

## 适用边界

- 探针默认 `RTLD_NOW` 局部作用域；`RTLD_GLOBAL`/visibility 改写/dlmopen
  变体未测。
- 仅实测 OHOS 6.0 SDK（clang-15，musl + libc++_shared）；其他 SDK 版本
  行为未对比。
- 本条定性"跨 DSO RTTI 同一性"这一层；chaiscript 侧的分派实现细节见
  DRAFT-chaiscript-6.1.0-constructor-stdlib-vs-dynload。
