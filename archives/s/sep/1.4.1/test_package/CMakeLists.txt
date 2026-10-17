cmake_minimum_required(VERSION 3.15)
project(sep_consumer_tests C)

find_package(sep CONFIG REQUIRED)

foreach(test_name IN ITEMS test_sep test_sep_errors test_sep_ohos)
  add_executable(${test_name} ${test_name}.c)
  target_compile_features(${test_name} PRIVATE c_std_11)
  target_link_libraries(${test_name} PRIVATE sep::sep)
endforeach()
