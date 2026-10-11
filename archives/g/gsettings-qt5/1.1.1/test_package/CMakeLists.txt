cmake_minimum_required(VERSION 3.18)
project(test_gsettings_qt5 LANGUAGES CXX)

# Qt5::Core：由依赖链里的 qt5-qtbase 提供（CMakeDeps 生成 Qt5Config.cmake）。
find_package(Qt5 COMPONENTS Core REQUIRED)

# 下游消费路径（kylin-calendar 用法）：pkg_check_modules(gsettings-qt)。
# GSETTINGS_QT_PC_DIR 指向被测包自己的 lib/pkgconfig，必须排在 PkgConfigDeps
# 生成的同名 .pc 之前，才能验证包内真身；gio-2.0 等传递依赖仍由 generators 提供。
find_package(PkgConfig REQUIRED)
set(ENV{PKG_CONFIG_PATH} "${GSETTINGS_QT_PC_DIR}:$ENV{PKG_CONFIG_PATH}")
pkg_check_modules(GSETTINGS_QT REQUIRED IMPORTED_TARGET gsettings-qt)

add_executable(test_gsettings_qt5 test_gsettings_qt5.cpp)
target_compile_features(test_gsettings_qt5 PRIVATE cxx_std_17)
target_link_libraries(test_gsettings_qt5 PRIVATE PkgConfig::GSETTINGS_QT Qt5::Core)
