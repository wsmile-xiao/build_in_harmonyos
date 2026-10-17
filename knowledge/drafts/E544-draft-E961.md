# E544 — cmake option() 缺 description 字符串导致功能被静默关闭

## 症状

`CMakeLists.txt` 明明写着 `option(LIBASD_BUILD_TESTS ON)`，但 `CMakeCache.txt` 中
`LIBASD_BUILD_TESTS:BOOL=OFF`，`test/` 子目录从未加入，`ctest` 注册 0 个用例且 configure/build 全绿。
另注意：Boost 缺失时的 `message(WARNING "all the tests are disabled")` 会误导排查方向——本例 Boost 在场，警告根本没打出来。

## 根因

CMake `option()` 签名是 `option(<variable> "description" [<value>])`。只有两个参数时，
第二个 token（`ON`）被当作 description，变量默认 OFF。上游源码的“看似 ON”实际是 OFF。

## 已验证方案（libasd 1.5.6）

1. 构建时显式传 `-DLIBASD_BUILD_TESTS=ON`（不依赖畸形 option 默认值）；
2. 补丁修正为 `option(LIBASD_BUILD_TESTS "Build the Boost.Test upstream test suite" ON)`，
   让上游默认值与文档意图一致。

修正后上游 6/6 用例在 OHOS PC 全部通过。扫描模式：
`grep -nE 'option\([A-Za-z_]+ (ON|OFF|TRUE|FALSE)\)'` —— 命中即此问题。

## 与 E321 的区别

E321 是“enable_testing() 但从不 add_test() → ctest 0 用例假绿”；本条是“option() 畸形签名 → 测试目标
根本没生成”。两类都要求“注册用例数 > 0”作为门禁，不能只看 ctest 退出码。

## 禁止

- 用 `-D<NAME>=OFF` 或 `set(... OFF)` 关闭测试来绕过（正是本条记录的静默跳过）。
