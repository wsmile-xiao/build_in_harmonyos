# leatherman

Puppet Labs 出品的 C++ 工具库集合（被 cpp-hocon、facter 等依赖的上游基础库），
包含 util、locale、logging、json_container、file_util、curl、dynamic_library、
execution、ruby 等组件。

- 上游：https://github.com/puppetlabs/leatherman
- 构建：CMake（静态库，上游默认 `LEATHERMAN_SHARED=FALSE`）
- 依赖：制品仓 `boost1.84` 系列包 + `curl`；Catch 与 rapidjson 随源码自带
- 测试：上游 `leatherman_test` 聚合二进制（Catch，ctest 注册 1 项，内含 101 个
  TEST_CASE/SCENARIO），配方在 `build()` 内真实执行并解析断言汇总。

## OHOS 适配

- Boost 垫片：`boost1.84` 系列包各自导出不同的 `cmake_file_name`
  （多包同名 `Boost` 会互相覆盖，见 boost1.84-fiber 配方注记），配方在
  `generate()` 内扫描各依赖包的 `libboost_*.a` 并生成统一的
  `BoostConfig.cmake`，上游 `find_package(Boost ...)` 无需打补丁。
- CURL 垫片：同理生成 `CURLConfig.cmake`，提供上游使用的
  `CURL_INCLUDE_DIRS` / `CURL_LIBRARIES` 变量。
- 不修改上游测试；`ENABLE_CXX_WERROR=OFF` 纯构建选项（clang 15 告警降级）。
- 移除包内上游自带的 `lib/cmake/leatherman` CMake 配置（与 Conan
  CMakeDeps 生成的配置冲突），消费者一律走 `find_package(leatherman)`。

## References

- https://github.com/puppetlabs/leatherman
- https://github.com/puppetlabs/cpp-hocon（下游，OHOS 已适配 0.3.0）
