cmake_minimum_required(VERSION 3.16)
project(i18n-demo LANGUAGES CXX)

# none | gettext | shim（由 conanfile.py 的 nls_mode 选项注入）
set(I18N_DEMO_NLS_MODE "shim" CACHE STRING "NLS handling mode: none|gettext|shim")

add_library(i18n-demo STATIC src/i18n.cpp)
target_include_directories(i18n-demo PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(i18n-demo PUBLIC cxx_std_17)
set_target_properties(i18n-demo PROPERTIES POSITION_INDEPENDENT_CODE ON)

if(I18N_DEMO_NLS_MODE STREQUAL "gettext")
  # 策略①：Conan(CMakeDeps) 生成 gettext-config.cmake，导出 gettext::gettext（libintl）
  find_package(gettext CONFIG REQUIRED)
  target_link_libraries(i18n-demo PUBLIC gettext::gettext)
elseif(I18N_DEMO_NLS_MODE STREQUAL "shim")
  # 策略③：平台/依赖没有可用 libintl.h 时，用样例附带的声明 + 恒等实现头兜底
  target_include_directories(i18n-demo PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/shim/include>
    $<INSTALL_INTERFACE:include/shim>)
endif()
# nls_mode=none：不提供任何 gettext 声明 —— 缺陷态，编译应当失败

add_executable(i18n-demo-cli src/i18n-demo.cpp)
target_link_libraries(i18n-demo-cli PRIVATE i18n-demo)

include(GNUInstallDirs)
install(TARGETS i18n-demo i18n-demo-cli
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY shim/include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/shim)
