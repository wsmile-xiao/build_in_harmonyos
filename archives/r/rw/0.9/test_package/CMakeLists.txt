cmake_minimum_required(VERSION 3.15)
project(test_rw LANGUAGES C)

find_package(rw CONFIG REQUIRED)

add_executable(test_rw test_rw.c)
target_compile_features(test_rw PRIVATE c_std_99)
target_link_libraries(test_rw PRIVATE rw::rw)

if(RW_EXPECT_OHOS)
  target_compile_definitions(test_rw PRIVATE RW_EXPECT_OHOS=1)
endif()
