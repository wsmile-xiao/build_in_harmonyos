cmake_minimum_required(VERSION 3.18)
project(test_vtk CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(VTK_TEST_RENDERING "Verify the configured rendering backend" ON)
option(VTK_TEST_EGL "Use the EGL render window" OFF)

set(_vtk_components CommonCore FiltersSources)
if(VTK_TEST_RENDERING)
    if(VTK_TEST_EGL)
        # Use paths detected from the profile's compiler, including its sysroot.
        find_path(VTK_EGL_INCLUDE EGL/egl.h
            HINTS ${CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES} REQUIRED)
        find_path(VTK_GLES3_INCLUDE GLES3/gl3.h
            HINTS ${CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES} REQUIRED)
        find_library(VTK_EGL_LIBRARY NAMES EGL
            HINTS ${CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES} REQUIRED)
        find_library(VTK_GLES3_LIBRARY NAMES GLESv3 GLESv2
            HINTS ${CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES} REQUIRED)
        if(NOT TARGET OpenGL::EGL)
            add_library(OpenGL::EGL UNKNOWN IMPORTED)
            set_target_properties(OpenGL::EGL PROPERTIES
                IMPORTED_LOCATION "${VTK_EGL_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${VTK_EGL_INCLUDE}")
        endif()
        if(NOT TARGET OpenGL::GLES3)
            add_library(OpenGL::GLES3 UNKNOWN IMPORTED)
            set_target_properties(OpenGL::GLES3 PROPERTIES
                IMPORTED_LOCATION "${VTK_GLES3_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${VTK_GLES3_INCLUDE}")
        endif()
        if(NOT TARGET OpenGL::GL)
            add_library(OpenGL::GL INTERFACE IMPORTED)
            set_property(TARGET OpenGL::GL PROPERTY
                INTERFACE_LINK_LIBRARIES OpenGL::GLES3)
        endif()
    endif()
    list(APPEND _vtk_components RenderingCore RenderingOpenGL2 CommonMisc GeovisCore)
endif()
find_package(VTK REQUIRED COMPONENTS ${_vtk_components})

get_filename_component(_vtk_lib_dir "${VTK_DIR}/../.." ABSOLUTE)
if(VTK_TEST_RUNTIME)
    set(_vtk_lib_dir "${VTK_TEST_RUNTIME}")
endif()
set(CMAKE_SKIP_RPATH OFF)
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
set(CMAKE_INSTALL_RPATH "${_vtk_lib_dir}")

add_executable(test_vtk src/main.cpp)
target_link_libraries(test_vtk PRIVATE VTK::CommonCore VTK::FiltersSources)
enable_testing()
add_test(NAME test_vtk COMMAND test_vtk)
if(VTK_TEST_RENDERING)
    add_executable(test_vtk_render src/test_render.cpp)
    target_link_libraries(test_vtk_render PRIVATE
        VTK::RenderingCore VTK::RenderingOpenGL2 VTK::FiltersSources)
    vtk_module_autoinit(TARGETS test_vtk_render MODULES
        VTK::RenderingCore VTK::RenderingOpenGL2 VTK::FiltersSources)
    if(VTK_TEST_EGL)
        target_compile_definitions(test_vtk_render PRIVATE VTK_TEST_EGL)
    endif()
    add_test(NAME test_vtk_render COMMAND test_vtk_render)
    add_executable(test_vtk_viewports src/test_viewports.cpp)
    target_link_libraries(test_vtk_viewports PRIVATE
        VTK::RenderingCore VTK::RenderingOpenGL2 VTK::FiltersSources
        VTK::CommonMisc VTK::GeovisCore)
    vtk_module_autoinit(TARGETS test_vtk_viewports MODULES
        VTK::RenderingCore VTK::RenderingOpenGL2 VTK::FiltersSources)
    if(VTK_TEST_EGL)
        target_compile_definitions(test_vtk_viewports PRIVATE VTK_TEST_EGL)
    endif()
    add_test(NAME test_vtk_viewports COMMAND test_vtk_viewports)
endif()
