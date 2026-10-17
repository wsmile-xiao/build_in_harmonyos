cmake_minimum_required(VERSION 3.16)
project(test_embedded_ringbuf_cpp CXX)

find_package(embedded_ringbuf_cpp REQUIRED)

# 钉死「测试靶向 == 交付物」：被测头必须来自本包的 include 目录，
# 并把它的 sha256 打进配置日志留证（便于与 conan cache 内实物比对）。
set(_hdr "")
foreach(_dir IN LISTS embedded_ringbuf_cpp_INCLUDE_DIRS)
    if(EXISTS "${_dir}/RingBufCPP.h")
        set(_hdr "${_dir}/RingBufCPP.h")
    endif()
endforeach()
if(_hdr STREQUAL "")
    get_target_property(_inc embedded_ringbuf_cpp::embedded_ringbuf_cpp
                        INTERFACE_INCLUDE_DIRECTORIES)
    message(FATAL_ERROR "RingBufCPP.h 未在包 include 目录中找到: ${_inc}")
endif()
file(SHA256 "${_hdr}" _hdr_sha256)
message(STATUS "under test: ${_hdr}")
message(STATUS "RingBufCPP.h sha256=${_hdr_sha256}")

add_executable(test_embedded_ringbuf_cpp test.cpp)
target_link_libraries(test_embedded_ringbuf_cpp
                      PRIVATE embedded_ringbuf_cpp::embedded_ringbuf_cpp)
