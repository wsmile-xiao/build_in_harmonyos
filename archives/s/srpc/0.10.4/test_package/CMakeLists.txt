cmake_minimum_required(VERSION 3.10)
project(test_package LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT SRPC_GENERATOR)
    message(FATAL_ERROR "SRPC_GENERATOR not provided by test_package conanfile")
endif()
if(NOT PROTOC_EXECUTABLE)
    message(FATAL_ERROR "PROTOC_EXECUTABLE not provided by test_package conanfile")
endif()

# 被测包：使用 srpc 安装的 srpc-config.cmake（提供 SRPC_INCLUDE_DIR /
# SRPC_LIB_DIR / SRPC_BIN_DIR）。
find_package(srpc REQUIRED CONFIG)

include_directories(${SRPC_INCLUDE_DIR} ${DEP_INCLUDE_DIRS} ${CMAKE_CURRENT_BINARY_DIR})
link_directories(${SRPC_LIB_DIR} ${DEP_LIBRARY_DIRS})

# 依赖（workflow）导出的编译宏：用裸库名链接时不会被 target 自动带入
if(DEP_DEFINES)
    add_compile_definitions(${DEP_DEFINES})
endif()

set(PROTO_SRC ${CMAKE_CURRENT_SOURCE_DIR}/src/echo.proto)
set(PROTO_OUT ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.cc ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.h)

# 消费者侧代码生成：protoc 产出消息类，srpc_generator 产出 RPC 桩头文件
add_custom_command(
    OUTPUT ${PROTO_OUT}
    COMMAND ${PROTOC_EXECUTABLE} --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
            -I${CMAKE_CURRENT_SOURCE_DIR}/src ${PROTO_SRC}
    DEPENDS ${PROTO_SRC}
    COMMENT "protoc: echo.proto -> echo.pb.h/echo.pb.cc")

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/echo.srpc.h
    COMMAND ${SRPC_GENERATOR} ${PROTO_SRC} ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS ${PROTO_SRC}
    COMMENT "srpc_generator: echo.proto -> echo.srpc.h")

add_custom_target(gen_echo ALL
    DEPENDS ${PROTO_OUT} ${CMAKE_CURRENT_BINARY_DIR}/echo.srpc.h)

set(SRPC_LINK_LIBS srpc workflow protobuf ssl crypto snappy lz4 z pthread)

add_executable(echo_server src/echo_server.cc ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.cc)
add_executable(echo_client src/echo_client.cc ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.cc)
add_dependencies(echo_server gen_echo)
add_dependencies(echo_client gen_echo)
target_link_libraries(echo_server PRIVATE ${SRPC_LINK_LIBS})
target_link_libraries(echo_client PRIVATE ${SRPC_LINK_LIBS})

enable_testing()
add_test(NAME consumer_rpc_roundtrip
         COMMAND sh ${CMAKE_CURRENT_SOURCE_DIR}/run_consumer_test.sh
                 $<TARGET_FILE:echo_server> $<TARGET_FILE:echo_client>)
