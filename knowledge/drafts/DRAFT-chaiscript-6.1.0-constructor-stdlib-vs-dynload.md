# DRAFT-chaiscript-6.1.0-constructor-stdlib-vs-dynload：构造函数形态决定是否 dlopen

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: chaiscript 6.1.0 HarmonyOS PC 适配（PR #8935，multithreaded_test 两轮定位）
> 对应：knowledge/drafts/DRAFT-chaiscript-6.1.0-constructor-stdlib-vs-dynload.kv

## 现象

真机跑上游 multithreaded_test 第一轮直接 `Signal 6 (core dumped)`，stderr 刷屏：

```text
Error loading shared library chaiscript_stdlib-6.1.0.so: No such file or directory
...
libc++abi: terminating due to uncaught exception of type chaiscript::exception::eval_error
```

补建 `chaiscript_stdlib-6.1.0` 模块第二轮：dlopen 与模块注册成功，转报
`to_string(const int)` 分派失败（进入另一条根因链）。

## 根因

同一引擎、两种构造形态，行为完全不同：

| 形态 | 位置 | stdlib 来源 | dlopen |
|------|------|-------------|--------|
| `chaiscript::ChaiScript chai;`（伞形头默认构造） | chaiscript.hpp:830 | 编译内置 `Std_Lib::library()` | 无（推荐） |
| `ChaiScript_Basic(std::move(parser), …)`（单参 explicit） | chaiscript_engine.hpp:323 | 运行时 `load_module("chaiscript_stdlib-" + version)` | 有，缺模块即抛 `load_module_error` → 测试进程典型 abort |

上游自建测试（multithreaded_test.cpp 等用 `create_chaiscript_stdlib()+parser`
写法）走模块路径，其 CMake 会构建模块目标 `chaiscript_stdlib-6.1.0.so`
（src/chaiscript_stdlib_module.cpp；`load_module` 依次尝试裸名/lib 前缀/
.so/.dll/.bundle 变体）；自建 harness 漏编该目标即触发第一轮现象。
OHOS 上即使补齐：跨 DSO type_info 失配使类型分派仍失败——见
DRAFT-chaiscript-6.1.0-cross-dso-typeinfo-identity。

## 方案

消费者与 test_package 一律伞形头默认构造：

```cpp
#include <chaiscript/chaiscript.hpp>
chaiscript::ChaiScript chai;          // stdlib 编译内置，零 dlopen
chai.eval<int>("40 + 2");
```

从 5.x 迁移注意：5.x 的 `ChaiScript()` 曾默认动态加载 stdlib，6.x 伞形头
已编译内置，不要照搬旧 load_module 逻辑；`grep -rn "ChaiScript_Basic("`
可扫出单参形态存量。

## 验证（真实证据）

- 第一轮（缺模块）：构造抛错 → Signal 6（设备日志留档）
- 第二轮（补建模块，CMake MODULE 目标 + `set_target_properties` 对齐
  `libchaiscript_stdlib-6.1.0.so` 命名）：加载注册成功，转跨 DSO 分派失败
- test_package 伞形头默认构造：本机 MSVC 与 OHOS 真机 8/8 断言全过

## 适用边界

- 5.x 历史行为未在本仓库实测，迁移以编译器报错为准。
- 模块版本号来自 `Build_Info::version()`，跨版本模块不通用。
