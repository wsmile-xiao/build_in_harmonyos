cmake_minimum_required(VERSION 3.5)
project(getdns_smoke C)

find_package(getdns REQUIRED)

add_executable(getdns_smoke src/getdns_smoke.c)
target_link_libraries(getdns_smoke PRIVATE getdns::getdns)

# __OHOS__ 由 OHOS 交叉编译 clang 自动定义，此处不额外注入——
# test 源码据此探测并打印真实平台名，验证交叉编译环境。
if(NOT CMAKE_C_FLAGS MATCHES "OHOS")
    # 无需人工干预：OHOS SDK 工具链文件自动定义 __OHOS__
endif()
