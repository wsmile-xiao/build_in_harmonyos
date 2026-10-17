cmake_minimum_required(VERSION 3.15)
project(test_rtlsdr C)

# conan(CMakeDeps) 生成的配置：公共头 rtl-sdr.h + librtlsdr.so（libusb 由
# 交付包的 cpp_info.requires 传递进来，用例需要它的描述符结构体声明）
find_package(rtlsdr CONFIG REQUIRED)

add_compile_options(-Wall)

add_executable(test_rtlsdr test_rtlsdr.c)
target_link_libraries(test_rtlsdr PRIVATE rtlsdr::rtlsdr)

# 用例用 ELF 符号介入伪造 USB 设备：必须把可执行文件里的 libusb_* 放进动态
# 符号表，才能对共享库 librtlsdr.so 内的调用生效。
set_target_properties(test_rtlsdr PROPERTIES ENABLE_EXPORTS ON)
if(UNIX)
  target_link_options(test_rtlsdr PRIVATE -Wl,--export-dynamic)
endif()
