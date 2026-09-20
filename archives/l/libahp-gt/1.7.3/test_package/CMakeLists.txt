cmake_minimum_required(VERSION 3.15)
project(libahp_gt_consumer C)

enable_testing()

find_package(ahp_gt CONFIG REQUIRED)

add_executable(libahp_gt_consumer test_ahp_gt.c)
target_link_libraries(libahp_gt_consumer PRIVATE ahp_gt::ahp_gt m)

add_test(NAME consumer_assertions COMMAND libahp_gt_consumer)
