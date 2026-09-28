cmake_minimum_required(VERSION 3.16)
project(test_robtk C)

set(CMAKE_C_STANDARD 99)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ROBTK REQUIRED IMPORTED_TARGET robtk)

# robtk is a source toolkit: locate its root, i.e. the include directory that
# contains the pugl/ subdirectory (upstream uses RW=<robtk dir>).
set(ROBTK_ROOT "")
foreach(d ${ROBTK_INCLUDE_DIRS})
    if(IS_DIRECTORY "${d}/pugl")
        set(ROBTK_ROOT "${d}")
    endif()
endforeach()
if(NOT ROBTK_ROOT)
    message(FATAL_ERROR "robtk toolkit root (with pugl/) not found in ${ROBTK_INCLUDE_DIRS}")
endif()
message(STATUS "robtk toolkit root: ${ROBTK_ROOT}")

# How the toolkit is consumed on HarmonyOS, shared by all test targets:
#  * RTK_GLES        - OpenGL ES backend instead of desktop GL/GLX
#  * RTK_OFFSCREEN   - the UI may render without a native window (pbuffer)
#  * HAVE_IDLE_IFACE - the host drives the event loop (no private UI thread)
#  * HAVE_LV2_1_18_6 - LV2 1.18 header layout (lv2/ui/ui.h)
#  * PLUGIN_SOURCE   - the plugin specific UI compiled into ui_gl.c
add_library(robtk_test_config INTERFACE)
target_compile_definitions(robtk_test_config INTERFACE
    RTK_GLES
    RTK_OFFSCREEN
    HAVE_IDLE_IFACE
    HAVE_LV2_1_18_6
    RTK_URI="http://gareus.org/oss/lv2/robtktest"
    RTK_GUI="robtktest"
    PLUGIN_SOURCE="${CMAKE_CURRENT_SOURCE_DIR}/robtk_test_ui.c"
)
target_include_directories(robtk_test_config INTERFACE ${ROBTK_ROOT})
target_link_libraries(robtk_test_config INTERFACE PkgConfig::ROBTK)

# Build the UI exactly like a downstream LV2 plugin does: ui_gl.c plus the
# HarmonyOS window/GL backend pugl/pugl_ohos.c.
add_library(robtk_ui OBJECT
    ${ROBTK_ROOT}/ui_gl.c
    ${ROBTK_ROOT}/pugl/pugl_ohos.c
)
target_link_libraries(robtk_ui PRIVATE robtk_test_config)

enable_testing()

# 1) HarmonyOS backend test (EGL/GLES, input bridge, frame read-back)
add_executable(test_pugl_ohos test_pugl_ohos.c ${ROBTK_ROOT}/pugl/pugl_ohos.c)
target_link_libraries(test_pugl_ohos PRIVATE robtk_test_config)
add_test(NAME pugl_ohos COMMAND test_pugl_ohos)

# 2) full toolkit UI test (LV2 UI entry point + widgets + GLES presentation)
add_executable(test_robtk_ui test_robtk_ui.c $<TARGET_OBJECTS:robtk_ui>)
target_link_libraries(test_robtk_ui PRIVATE robtk_test_config)
add_test(NAME robtk_ui COMMAND test_robtk_ui)
