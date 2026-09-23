cmake_minimum_required(VERSION 3.15)
project(test_boost_math CXX)

find_package(BoostMath REQUIRED CONFIG COMPONENTS tr1 tr1f c99)

add_executable(test_boost_math test_boost_math.cpp)
target_link_libraries(test_boost_math PRIVATE BoostMath::tr1 BoostMath::tr1f BoostMath::c99)

enable_testing()
add_test(NAME boost_math_test COMMAND test_boost_math)
