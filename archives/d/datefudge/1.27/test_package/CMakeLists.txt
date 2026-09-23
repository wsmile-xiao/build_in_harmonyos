cmake_minimum_required(VERSION 3.15)
project(datefudge_test C)

add_executable(test_datefudge test_datefudge.c)

if(DATEFUDGE_EXPECT_OHOS)
  target_compile_definitions(test_datefudge PRIVATE DATEFUDGE_EXPECT_OHOS=1)
endif()

