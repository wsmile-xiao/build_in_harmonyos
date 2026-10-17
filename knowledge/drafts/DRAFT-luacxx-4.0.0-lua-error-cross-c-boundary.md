# OHOS 上 C++ 异常无法跨无 unwind tables 的 Lua C 边界：闭包入口异常转换

> 状态：草稿（DRAFT，待人工审核）｜来源：luacxx 4.0.0 OHOS aarch64 适配（pc7-38，2026-09-28）
> similar_to: DRAFT-E5xx-ohos-musl-unwind-tables-empty-stacktrace, E507

## 问题

在 OHOS（HarmonyOS PC, musl）上用 luacxx（C++ Lua 绑定库）运行上游测试时，
`error_support` 用例以 **SIGABRT / "uncaught exception"** 终止，而不是预期的可捕获异常：

```text
libc++abi: terminating due to uncaught exception of type lua::error: Function expects at least 1 argument but none were given
stack traceback:
stack: Lua stack (0 items):
Signal 6 (core dumped)
```

最小复现：`lua::push_function<void(bool)>` 注册闭包后，以不足参数调用
`lua::call<void>(env["call"])`——闭包内 `invoke_callable` 检查参数数并 `throw lua::error`，
该异常无法穿回 C++ 侧，进程直接 abort。

## 根因

1. OHOS 制品仓的 `liblua.a`（lua/5.4.8，纯 C 编译）**没有发射 `.eh_frame` / unwind tables**
   （`readelf -S` 无异常展开表，musl 工具链默认行为）；
2. luacxx 把 `std::function` 经 `lua_pushcclosure(state, invoke_callable<RV,Args...>, 1)`
   注册为 Lua C 函数；
3. 闭包内抛出的 C++ `lua::error` 需要穿过 `lua_pcall → luaD_call → 闭包` 的 C 帧
   才能回到 C++ 侧，但缺失展开表时 unwinder 无法跨 C 边界 → `std::terminate`。

与 `DRAFT-E5xx`（栈回溯空帧）同根（musl 无 unwind tables），但症状与修复路径不同。

## 方案（源码最小补丁，无平台宏）

在 `invoke_callable<RV, Args...>` 模板入口加异常转换，与库自身 `lua::callable`
路径（`src/convert/callable.cpp`）既有模式一致：

```cpp
template <typename RV, typename... Args>
int invoke_callable(lua_State* const state)
{
    try {
        auto wrapped = lua::get_userdata_block(state, lua_upvalueindex(1))
            ->cast<std::function<RV(Args...)>>(state);
        // ...原逻辑（参数校验、Invoke）...
        return Invoke<decltype(*wrapped), RV, Args..., ArgStop>::template invoke<>(*wrapped, index);
    } catch (lua::error& ex) {
        // 在闭包入口把 C++ 异常转换为 Lua 错误，避免跨纯 C Lua 边界展开
        lua::push(state, ex);
        lua_error(state);
        throw std::logic_error("lua_error must never return");
    }
}
```

转换后 `lua_pcall` 正常返回 `LUA_ERRRUN`，由封装层（`algorithm.cpp`）抛回 C++ 侧
`lua::error`，调用方照常捕获。

## 验证

- `error_support` 用例：修复前 SIGABRT（6 项断言中第 2 项即 abort）→ 修复后 **6/6 断言通过**；
- 上游全量：`luacxx_test_main`（34 项）+ `luacxx_test_without_conversion`（1 项）全部通过；
- 鸿蒙专项测试（`__OHOS__` 目标校验 + Lua 往返调用）PASSED；
- `conan create`（ohos-aarch64）G2 干净构建，test_package 消费者仅用公开 API PASSED。

## 适用边界 / 反例

- **适用**：OHOS 上任何把 C++ callable 经 `lua_pushcclosure` 注入**纯 C 编译、无 unwind tables** 的
  Lua 的绑定库；以及 C++ 异常需穿过无展开表第三方纯 C 库边界的场景。
- **反例**：若目标 Lua 构建带完整 `.eh_frame`（如 glibc 生态发行版），异常可直接跨边界，
  无需该转换；若闭包注册路径本身已含异常转换，重复添加无益。
- **不做**：不得用 `__OHOS__` 平台宏限定该修复（R8）——机制由展开表决定，与平台名无关。

## 关联

- `similar_to`: DRAFT-E5xx（unwind tables 缺失，栈回溯空帧）、E507（pthread 取消 API 缺失）
- 归档同 PR：`archives/l/luacxx/4.0.0/`（补丁 `0002-include-luacxx-convert-callable.hpp.patch`）
