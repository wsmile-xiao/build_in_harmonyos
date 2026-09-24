cmake_minimum_required(VERSION 3.15)
project(test_dirent C)

# 直接加载包内已安装的物理 CMake 配置（非 CMakeDeps 生成物），
# 使消费者真实依赖包制品目录（lib/cmake/Dirent-1.26/）。
include("${DIRENT_PACKAGE_FOLDER}/lib/cmake/Dirent-1.26/DirentConfig.cmake")

add_executable(test_dirent test_dirent.c)
target_link_libraries(test_dirent PRIVATE dirent)
set_target_properties(test_dirent PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)

# HarmonyOS 专项测试: 独立于上游与通用消费者用例, 针对 OHOS 运行环境
# 验证目录枚举/d_type 分类/scandir 排序/telldir-seekdir 回跳的真实语义。
add_executable(test_ohos_dirent test_ohos_dirent.c)
target_link_libraries(test_ohos_dirent PRIVATE dirent)
set_target_properties(test_ohos_dirent PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)