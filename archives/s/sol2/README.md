# sol2

sol2 3.5.0 是面向 Lua 的 C++ 绑定库。本适配按 header-only 库打包，安装
`include/sol/` 和 `sol2::sol2` CMake 消费目标，不生成二进制库。

## HarmonyOS 适配

- 上游版本：3.5.0
- 上游仓库：https://github.com/ThePhD/sol2
- 适配路径：基础适配
- 许可证：MIT
- Conan 引用：`sol2/3.5.0`

配方不引入 Lua 运行时依赖；需要执行 Lua 脚本的消费者自行提供 Lua。

## 测试

上游 `tests/` 目录包含 342 个 Catch2 注册（339 个 `TEST_CASE` + 3 个
`TEMPLATE_LIST_TEST_CASE`），但 release 源码未携带
可复现的 LuaBuild/Catch2 测试依赖，因此配方没有伪造上游测试通过数。
`test_package` 用 CMake 消费目标编译，并验证版本宏与 `sol::optional` API。

详细统计和验证记录见 [3.5.0/notes.md](3.5.0/notes.md) 与
[3.5.0/test_package/MANIFEST.yml](3.5.0/test_package/MANIFEST.yml)。
