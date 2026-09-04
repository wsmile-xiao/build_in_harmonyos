cmake_minimum_required(VERSION 3.15)
project(test_brpc CXX)

# protobuf 制品仓 cmake_find_mode=none：CMakeDeps 不为其生成 config/target，
# 而 brpc_DEPS_TARGET 引用 protobuf::protobuf。先加载 protobuf 包内安装的
# 上游 config（protobuf_DIR 由 conan_toolchain 注入），并创建 brpc_DEPS_TARGET
# 期望的聚合 target 别名。
find_package(Protobuf CONFIG REQUIRED)
if(NOT TARGET protobuf::protobuf)
    add_library(protobuf::protobuf INTERFACE IMPORTED)
    set_target_properties(protobuf::protobuf PROPERTIES
        INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
endif()

find_package(brpc REQUIRED)

# protobuf 静态链已由 protobuf::libprotobuf 聚合 target 提供
# gflags/leveldb 的 public 头（butil/logging.h 引用 gflags/gflags_declare.h）
# 通过显式依赖 target 的 INTERFACE include 传递到编译期。
set(PROTOC "${PROTOBUF_PREFIX}/bin/protoc")

find_package(gflags CONFIG REQUIRED)
find_package(leveldb CONFIG REQUIRED)

set(PROTO_SRC ${CMAKE_CURRENT_SOURCE_DIR}/echo.proto)
set(PROTO_HDR ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.h)
set(PROTO_CC ${CMAKE_CURRENT_BINARY_DIR}/echo.pb.cc)
add_custom_command(
    OUTPUT ${PROTO_HDR} ${PROTO_CC}
    COMMAND ${PROTOC} --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
            -I${CMAKE_CURRENT_SOURCE_DIR} ${PROTO_SRC}
    DEPENDS ${PROTO_SRC}
    COMMENT "Generating echo.pb.{h,cc} from echo.proto"
    VERBATIM
)

add_executable(test_brpc test_brpc.cpp ${PROTO_CC})
target_include_directories(test_brpc PRIVATE
    ${CMAKE_CURRENT_BINARY_DIR}
    ${PROTOBUF_PREFIX}/include
)
target_link_libraries(test_brpc brpc::brpc gflags::gflags leveldb::leveldb protobuf::libprotobuf)

enable_testing()
add_test(NAME test_brpc COMMAND test_brpc)
