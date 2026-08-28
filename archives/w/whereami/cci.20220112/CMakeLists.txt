cmake_minimum_required(VERSION 3.15)
project(whereami LANGUAGES C)

set(WHEREAMI_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/src")

add_library(whereami "${WHEREAMI_SOURCE_DIR}/whereami.c")
target_include_directories(whereami PUBLIC
    $<BUILD_INTERFACE:${WHEREAMI_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)
target_compile_features(whereami PRIVATE c_std_99)

if(WHEREAMI_OHOS)
    target_compile_definitions(whereami PRIVATE __linux__ _GNU_SOURCE WAI_USE_DLADDR)
    target_link_libraries(whereami PUBLIC dl)
endif()

include(GNUInstallDirs)
install(TARGETS whereami
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES "${WHEREAMI_SOURCE_DIR}/whereami.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
