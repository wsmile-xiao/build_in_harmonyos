cmake_minimum_required(VERSION 3.15)
project(disomaster LANGUAGES CXX)

# 查找 Qt5（由 CMakeDeps 生成配置文件）
find_package(qt5-qtbase CONFIG REQUIRED)

# 源码目录和 moc 生成文件路径由 CMakeToolchain cache variables 传入
# DISOMASTER_SOURCE_DIR: 上游源码根目录（含 libdisomaster/ 子目录）
# DISOMASTER_MOC_SOURCE: conanfile 生成的 moc_disomaster.cpp 路径

add_library(disomaster SHARED
    "${DISOMASTER_SOURCE_DIR}/libdisomaster/disomaster_cli.cpp"
    "${DISOMASTER_MOC_SOURCE}"
)

# 仅链接 Qt5Core 组件（避免引入 Gui/Network/Test/Concurrent 等不必要的依赖）
target_link_libraries(disomaster PUBLIC Qt5::Core)

target_include_directories(disomaster PUBLIC
    "${DISOMASTER_SOURCE_DIR}/libdisomaster"
)

# 手动添加 Qt5 include 目录（CMakeDeps 组件级 includedirs 在此环境未正确传递）
if(DEFINED QT5_INCLUDE_DIR)
    target_include_directories(disomaster PRIVATE ${QT5_INCLUDE_DIR})
endif()
if(DEFINED QT5_CORE_INCLUDE_DIR)
    target_include_directories(disomaster PRIVATE ${QT5_CORE_INCLUDE_DIR})
endif()

target_compile_features(disomaster PRIVATE cxx_std_11)

# OHOS 平台需要使用 libc++ 运行时
if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    target_link_options(disomaster PRIVATE -stdlib=libc++)
endif()

# 安装共享库
install(TARGETS disomaster
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

# 安装头文件到 include/disomaster/
install(FILES "${DISOMASTER_SOURCE_DIR}/libdisomaster/disomaster.h"
    DESTINATION include/disomaster
)
