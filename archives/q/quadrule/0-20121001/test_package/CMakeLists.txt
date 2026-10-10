cmake_minimum_required(VERSION 3.15)
project(quadrule_test_package C)

find_package(quadrule CONFIG REQUIRED)

add_executable(quadrule_tests test_quadrule.c)
target_link_libraries(quadrule_tests PRIVATE quadrule::quadrule)
target_compile_features(quadrule_tests PRIVATE c_std_99)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
  target_compile_definitions(quadrule_tests PRIVATE QUADRULE_TEST_HARMONYOS=1)
endif()

enable_testing()
foreach(scenario
    legendre
    hermite
    laguerre
    clenshaw_curtis
    rule_adjust
    helpers
    summer
    ohos_aarch64_abi)
  add_test(NAME quadrule_${scenario} COMMAND quadrule_tests ${scenario})
endforeach()
