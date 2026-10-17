cmake_minimum_required(VERSION 3.15)
project(test_boost_defaults CXX)

# 元包消费语义验证：
#   1. find_package(Boost) —— boost-defaults requires 的 boost/1.90.0 经
#      CMakeDeps 传播出 Boost 配置文件；
#   2. Boost::boost 头文件目标（boost 包的默认组件）；
#   3. boost-defaults 元包自身配置 + 元组件目标 boost-defaults::boost_defaults
#      （package_info 暴露的默认组件集映射）；
#   4. Boost::unit_test_framework 编译库目标（boost 包组件）。
find_package(Boost REQUIRED)
find_package(boost-defaults REQUIRED)

add_executable(test_boost_defaults test.cpp)
# 优先链接元组件目标（验证 boost-defaults 命名空间可用），
# 同时链接 boost 头文件目标与 Boost.Test 编译库。
target_link_libraries(test_boost_defaults
    PRIVATE
        boost-defaults::boost_defaults
        Boost::boost
        Boost::unit_test_framework
)

enable_testing()
add_test(NAME test_boost_defaults COMMAND test_boost_defaults)
