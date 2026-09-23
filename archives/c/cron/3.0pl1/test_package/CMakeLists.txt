cmake_minimum_required(VERSION 3.15)
project(test_cron C)

add_executable(test_cron test.c)
add_executable(test_cron_ohos test_ohos.c)

enable_testing()
add_test(NAME test_cron COMMAND test_cron)
add_test(NAME test_cron_ohos COMMAND test_cron_ohos)
