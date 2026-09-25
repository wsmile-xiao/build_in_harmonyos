cmake_minimum_required(VERSION 3.15)
project(libg15render_test_package C)

find_package(libg15render CONFIG REQUIRED)

add_executable(test_libg15render test_libg15render.c)
target_link_libraries(test_libg15render PRIVATE libg15render::libg15render)

add_executable(test_libg15render_ohos test_libg15render_ohos.c)
target_link_libraries(test_libg15render_ohos PRIVATE libg15render::libg15render)
