cmake_minimum_required(VERSION 3.15)
project(test_portsmf LANGUAGES CXX)

enable_testing()
find_package(portsmf CONFIG REQUIRED)

add_executable(test_portsmf test_portsmf.cpp)
target_compile_features(test_portsmf PRIVATE cxx_std_11)
target_link_libraries(test_portsmf PRIVATE portsmf::portsmf)

set(PORTSMF_CONSUMER_TESTS
    sequence_construction
    note_insertion
    unit_conversion
    tempo_map
    time_signature
    serialization
    midi_round_trip
    ohos_aarch64_abi
)

list(LENGTH PORTSMF_CONSUMER_TESTS test_count)
math(EXPR last_test "${test_count} - 1")
foreach(test_index RANGE 0 ${last_test})
    list(GET PORTSMF_CONSUMER_TESTS ${test_index} test_name)
    math(EXPR case_number "${test_index} + 1")
    add_test(NAME ${test_name} COMMAND test_portsmf ${case_number})
    set_tests_properties(${test_name} PROPERTIES TIMEOUT 30)
endforeach()
