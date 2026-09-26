# robin (robin-map) 1.4.1 适配笔记

## 基本信息

- 上游项目：Tessil/robin-map 1.4.1
- 类型：C++17 header-only 库
- 构建系统：上游 CMake 安装规则
- 外部运行时依赖：无
- 上游测试框架：Boost.Test（测试期依赖）

## 适配过程

1. 使用上游 tag `v1.4.1` 官方归档包，`conandata.yml` 记录 SHA256；镜像回退由 CI 统一追加。
2. 配方仅安装公开头文件 `include/tsl/*.h`、上游 CMake package 配置和 LICENSE，不修改上游源码。
3. 通过 `cmake.configure()` + `cmake.install()` 调用上游安装规则；`package_type` 为 `header-library`，消费端不会链接额外库。
4. 上游测试文件原样放入 `test_package/upstream_tests/`，使用 Boost.Test 1.84.0 在 OpenDesk 真机编译运行；测试依赖只在 `test_package` 中声明，不传播给 robin 的普通消费者。

## 上游测试

上游 `tests/` 包含 5 个源文件。测试逻辑、输入和断言未修改；`test_package` 只提供消费者构建入口。Boost.Test 在 OpenDesk 真机报告 `Running 132 test cases`，0 失败、0 跳过。

## 验证结果

- 构建/安装：通过
- 上游测试：在 OpenDesk HarmonyOS aarch64 真机执行，132/132 通过
- 运行器输出：`UPSTREAM_TEST_RESULT total=132 failures=0 errors=0 skipped=0`
- 消费者验收：`conan create` 全部通过
