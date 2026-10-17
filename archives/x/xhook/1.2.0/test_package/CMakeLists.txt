cmake_minimum_required(VERSION 3.15)
project(test_xhook LANGUAGES C)

find_package(xhook CONFIG REQUIRED)

# libhooktarget.so: a dlopen-able library that calls malloc via its PLT in a
# loop from a background thread (mirrors upstream libtest/jni/test.c).
add_library(hooktarget SHARED hook_target.c)

# test_plt_hook: consumer that registers an xhook for malloc in the target
# library and verifies the hook actually fires (mirrors upstream
# libbiz/jni/biz.c + xhookwrapper demo app).
add_executable(test_plt_hook hook_main.c)
target_link_libraries(test_plt_hook PRIVATE xhook::xhook ${CMAKE_DL_LIBS} pthread)
set_target_properties(test_plt_hook PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

# target must sit next to the test binary so dlopen("./libhooktarget.so") resolves
add_custom_command(TARGET test_plt_hook POST_BUILD
                   COMMAND ${CMAKE_COMMAND} -E copy_if_different
                           $<TARGET_FILE:hooktarget> $<TARGET_FILE_DIR:test_plt_hook>/libhooktarget.so)
