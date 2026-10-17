cmake_minimum_required(VERSION 3.15)
project(test_sshfs C)

# sshfs is an application (not a library) — test by running the binary
add_executable(test_sshfs test.c)

enable_testing()
add_test(NAME test_sshfs COMMAND test_sshfs)
# 不要覆盖 PATH：conanrun 环境会把 sshfs 的 bin 目录注入 PATH，
# 若在此处强制 PATH=$ENV{PATH} 会在 ctest 运行时丢失该注入。
