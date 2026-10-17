cmake_minimum_required(VERSION 3.15)
project(ohos_spsc_consumer LANGUAGES CXX)

# 真实消费者工程：消费 spscqueue 1.1（header-only）的 SPSCQueue<T> API
# 本测试在 OHOS 设备（aarch64-linux-ohos clang）上实际编译运行。
# 直接以 target_include_directories 引用归档内头文件（header-only 库无需 find_package）。

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Threads REQUIRED)

add_executable(ohos_spsc_test main.cpp)
target_include_directories(ohos_spsc_test PRIVATE
    "${SPSCQUE_SOURCE_DIR}/include"
)
target_link_libraries(ohos_spsc_test PRIVATE Threads::Threads)

enable_testing()
add_test(NAME ohos_spsc_test_run COMMAND ohos_spsc_test)