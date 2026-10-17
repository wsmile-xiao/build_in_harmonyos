cmake_minimum_required(VERSION 3.15)
project(test_libnvmemi C)

# conan(CMakeDeps) 生成的配置：头文件 nvme/*.h + 库 libnvme-mi.so
find_package(libnvmemi CONFIG REQUIRED)

# 必须在 add_executable() 之前：目录属性在目标创建时快照，置于其后则本目标收不到 -Wall
add_compile_options(-Wall)

add_executable(test_libnvmemi test_libnvme_mi.c)
target_link_libraries(test_libnvmemi PRIVATE libnvmemi::libnvmemi)

# 用例在进程内伪造 MCTP 设备：需要把可执行文件里的 socket()/sendmsg() 放进
# 动态符号表，才能对共享库内的调用生效（ELF 符号介入）。
set_target_properties(test_libnvmemi PROPERTIES ENABLE_EXPORTS ON)
if(UNIX)
  target_link_options(test_libnvmemi PRIVATE -Wl,--export-dynamic)
endif()

