# sol2 3.5.0 适配笔记

## 基本信息

- 上游：https://github.com/ThePhD/sol2
- 版本：3.5.0
- 构建类型：header-only C++ 库
- Conan 引用：`sol2/3.5.0`
- 源码 SHA256：`86c0f6d2836b184a250fc2907091c076bf53c9603dd291eaebade36cc342e13c`

## 适配内容

配方从官方 v3.5.0 源码归档取出 `include/` 和 `LICENSE.txt`，不编译或打包
Lua。`package_info()` 暴露 `sol2::sol2` CMake target，链接库列表为空。

本次保留四个补丁：

1. `0001-include-sol-ebco.hpp.patch`：为 `ebco` 各特化增加 tagged construction，
   消除 OHOS Clang 在包装类型构造时的重载歧义。
2. `0002-include-sol-types.hpp.patch`：显式解包 container proxy，并保持表值的
   const/lvalue 语义，修复 OHOS Clang 下的容器代理构造。
3. `0003-include-sol-usertype_container.hpp.patch`：关联容器迭代结束判断使用
   sol2 的 `sen()` 哨兵访问器。
4. `0004-include-sol-usertype_storage.hpp.patch`：`__newindex` 对命名 usertype
   也查找静态 property/variable setter，避免把 Lua 值直接写入而绕过 C++ setter。

## 测试用例核对

- 上游 `tests/` 静态统计为 342 个注册（339 个 `TEST_CASE` + 3 个
  `TEMPLATE_LIST_TEST_CASE`），2,312 个断言宏。
- 远端实际启用并运行了 306 个 Catch2 用例，3,689 个展开后的断言：301 个用例
  和 3,680 个断言通过；5 个用例、9 个断言失败。静态注册数不能直接当作实际
  执行数，模板展开和测试配置会改变实际数量。
- 上游构建目标为 `sol2.tests.run_time`，使用 `make -j1`。四个 Catch2 空标签
  仅在远端临时测试副本中改为 `[upstream]`，没有修改或提交上游测试源码。
- `overflow.cpp:59` 只因上游 `-Werror` 与 OHOS Clang 的 unused-but-set-variable
  告警冲突，在远端目标的临时 `flags.make` 中加入了
  `-Wno-error=unused-but-set-variable`；该测试构建调整没有进入配方。
- `test_package/test.cpp` 是 1 个消费者用例，包含 3 个版本宏编译期断言和 1
  个 `sol::optional` 运行期检查，共 4 个断言。

## 上游失败逐项定位

以下失败均来自同一份最终四补丁源码；没有把失败伪报为通过：

- `usertypes/unregister/re-register`：
  `tests/run_time/source/usertypes.unregister.cpp:78` 的
  `safe_script("assert(u:f() == 'registered')")` 在注销后重新注册时返回无效，
  错误为 `attempt to index a userdata value (global 'u')`。这是 OHOS Lua 在同一
  state 中重新注册已注销 usertype 的运行时限制。
- `containers/sequence containers`：
  `container_semantics.cpp:92` 的四个模板实例均因脚本使用未定义的 `issuec` 而
  失败；`rg` 在 `tests/run_time/source` 中找不到该变量定义，属于上游测试源码缺陷。
- `containers/append idiom`：
  `containers.cpp:411` 观察到 `vec2.size()` 为 3 而预期 4；前置 Lua 脚本在
  `containers.cpp:390-391` 使用未定义的 `issuevec`，同样属于上游测试源码缺陷。
- `containers/associative ordered pairs`：
  `container_semantics.ordered.cpp:273` 的 map 和 multimap 两个 section 均出现
  `data != reflect`。测试传递未注册的 `bar*` 值经过 Lua 往返，在 OHOS 运行时无法
  重建等价指针值，属于 OHOS Lua/sol2 对未注册指针值的限制。
- `policies/stack_dependencies`：
  `policies.cpp:206` 的 `c = dor.comp` 返回无效，错误为
  `attempt to index a userdata value (global 'dor')`；这是 OHOS Lua 在
  `stack_dependencies` usertype 访问路径上的运行时限制。

静态 property 和 variable 的回归已单独复核：`usertype/static-properties` 为
3/3 assertions，`usertype/vars` 为 15/15 assertions，均通过。

## 验证

设备端使用 host/build 都指向绝对路径
`/storage/Users/currentUser/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64`
的 Conan profile。`conan create` 返回码为 0；四个补丁均由 `patch_ng` 成功应用，
包创建成功，test_package 配置、编译、运行均成功。

上游运行命令为：

```text
cd /storage/Users/currentUser/tmp/sol2-final-upstream-run-2e2cd0594e/build/tests/run_time
../../x64/bin/sol2.tests.run_time --reporter compact
```

结果为：

```text
test cases:  306 |  301 passed | 5 failed
assertions: 3689 | 3680 passed | 9 failed
```

**编译结束**：2026-09-02

**最终状态**：built
