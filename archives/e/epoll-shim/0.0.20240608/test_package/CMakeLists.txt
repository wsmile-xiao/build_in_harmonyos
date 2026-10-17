cmake_minimum_required(VERSION 3.15)
project(test_epoll_shim C)

# Find the package via Conan-generated CMakeDeps
find_package(epoll-shim REQUIRED)

add_executable(test_epoll_shim test.c)
target_link_libraries(test_epoll_shim epoll-shim::epoll-shim)
# Disable epoll-shim wrapper macros (close/fcntl redirection) since on OHOS
# the native epoll is used and epoll_shim_close/epoll_shim_fcntl are not linked.
target_compile_definitions(test_epoll_shim PRIVATE EPOLL_SHIM_DISABLE_WRAPPER_MACROS)

enable_testing()
add_test(NAME test_epoll_shim COMMAND test_epoll_shim)
