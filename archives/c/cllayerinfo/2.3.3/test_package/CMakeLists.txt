cmake_minimum_required(VERSION 3.15)
project(test_cllayerinfo C)

find_package(opencl-headers REQUIRED)

# 消费者侧 dummy OpenCL 层：实现 clGetLayerInfo / clInitLayer，
# 供被测二进制在 OPENCL_LAYERS 指向它时枚举出层信息
# （复刻上游 tests/testsuite-standard.at 的 cllayerinfo 用例）。
add_library(testlayer MODULE test_layer.c)
target_link_libraries(testlayer PRIVATE opencl-headers::opencl-headers)

# 上游的层也是 -module 方式构建的（Makefile.am: libdummylayer_la_LDFLAGS = -module），
# 但层由 loader 用 dlopen 按绝对路径加载，无 soname 要求。
set_target_properties(testlayer PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "testlayer"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

# 消费者侧 dummy OpenCL ICD（安装驱动）：loader 只有在找到至少一个可用 ICD 时
# 才会去读 OPENCL_LAYERS 并初始化层（ocl_icd_loader.c: _num_icds == 0 直接中止），
# 所以要让 cllayerinfo 枚举出层，就必须先提供一个 dummy ICD。
add_library(testicd MODULE test_icd.c)
target_link_libraries(testicd PRIVATE opencl-headers::opencl-headers)
set_target_properties(testicd PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "testicd"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
