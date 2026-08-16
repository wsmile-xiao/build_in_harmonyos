cmake_minimum_required(VERSION 3.15)
project(test_libexif C)

# Find the package via Conan-generated CMakeDeps
find_package(libexif REQUIRED)

add_executable(test_libexif test.c)
target_link_libraries(test_libexif libexif::libexif)

# OOM 鲁棒性补全测试 (R34 扩展): ExifMem 失败分配器注入 + RLIMIT_AS 限制
# --builtin 使用内置 EXIF 数据，无需外部文件，ctest 可直接执行
add_executable(oom-test oom-test.c)
target_link_libraries(oom-test libexif::libexif)

enable_testing()
add_test(NAME test_libexif COMMAND test_libexif)
add_test(NAME oom_test_fail_early COMMAND oom-test --fail-n 1 --builtin)
add_test(NAME oom_test_fail_mid COMMAND oom-test --fail-n 8 --builtin)
add_test(NAME oom_test_fail_late COMMAND oom-test --fail-n 32 --builtin)
add_test(NAME oom_test_rlimit COMMAND oom-test --rlimit 8 --builtin)
