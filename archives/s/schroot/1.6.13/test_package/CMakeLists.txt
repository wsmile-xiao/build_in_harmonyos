cmake_minimum_required(VERSION 3.15)
project(schroot_consumer CXX)

# 消费者用例：编译一个真实调用 sbuild 公共 API 的程序并链接包内 libsbuild.a，
# 验证 schroot 的库在目标平台（aarch64-linux-ohos）上可用。
# schroot 的包只提供静态库与 pkg-config 文件（未导出 CMake 目标），且 sbuild 的
# 公共头文件依赖 boost，因此这里使用 test_package/conanfile.py 从各依赖包实际
# 安装路径收集到的头文件目录、库目录与库名。
add_executable(schroot_consumer src/schroot_consumer.cpp)
target_include_directories(schroot_consumer PRIVATE ${SCHROOT_INCLUDE_DIRS})
target_link_directories(schroot_consumer PRIVATE ${SCHROOT_LIBRARY_DIRS})
target_link_libraries(schroot_consumer PRIVATE "${SCHROOT_SBUILD_LIB}" ${SCHROOT_LIBRARIES})

# sbuild 的公共头文件会引入 boost；HarmonyOS 的 libc（musl）不提供
# pthread_setcancelstate()，与 schroot 自身构建一样需要关闭 boost 的对应封装。
target_compile_definitions(schroot_consumer PRIVATE BOOST_SP_NO_PTHREAD_SETCANCELSTATE)
