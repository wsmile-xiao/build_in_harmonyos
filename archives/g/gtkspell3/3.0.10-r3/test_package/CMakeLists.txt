cmake_minimum_required(VERSION 3.15)
project(test_gtkspell3 C)

# gtk/3.24.43 不声明 cpp_info.requires（扁平包），CMakeDeps 无法传递
# harfbuzz 等传递头文件；改用 pkg-config 解析完整 Requires 链
# （glib-2.0 gtk+-3.0 enchant-2）—— gtkdatabox 先例。
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTKSPELL3 REQUIRED gtkspell3-3.0)

set(GTKSPELL3_CLEAN_INCLUDE_DIRS)
foreach(inc_dir IN LISTS GTKSPELL3_INCLUDE_DIRS)
    if(EXISTS "${inc_dir}")
        list(APPEND GTKSPELL3_CLEAN_INCLUDE_DIRS "${inc_dir}")
    endif()
endforeach()

set(GTKSPELL3_CLEAN_CFLAGS)
foreach(flag IN LISTS GTKSPELL3_CFLAGS_OTHER)
    if(NOT flag MATCHES "^[A-Za-z]+:$")
        list(APPEND GTKSPELL3_CLEAN_CFLAGS "${flag}")
    endif()
endforeach()

set(GTKSPELL3_CLEAN_LDFLAGS)
foreach(flag IN LISTS GTKSPELL3_LDFLAGS_OTHER)
    if(NOT flag MATCHES "^[A-Za-z]+:$")
        list(APPEND GTKSPELL3_CLEAN_LDFLAGS "${flag}")
    endif()
endforeach()

add_executable(test_gtkspell3 test.c)
target_include_directories(test_gtkspell3 PRIVATE ${GTKSPELL3_CLEAN_INCLUDE_DIRS})
target_link_directories(test_gtkspell3 PRIVATE ${GTKSPELL3_LIBRARY_DIRS})
target_link_libraries(test_gtkspell3 PRIVATE ${GTKSPELL3_LIBRARIES} ${GTKSPELL3_CLEAN_LDFLAGS})
target_compile_options(test_gtkspell3 PRIVATE ${GTKSPELL3_CLEAN_CFLAGS})

enable_testing()
add_test(NAME test_gtkspell3 COMMAND test_gtkspell3)
