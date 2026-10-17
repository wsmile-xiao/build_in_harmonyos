cmake_minimum_required(VERSION 3.16)
project(test_boost_compiled CXX)

find_package(Boost REQUIRED COMPONENTS atomic chrono filesystem program_options regex serialization thread timer)

add_executable(test_boost_compiled test.cpp)
if(WIN32)
    target_compile_definitions(test_boost_compiled PRIVATE _WIN32_WINNT=0x0602)
endif()
target_link_libraries(
    test_boost_compiled
    PRIVATE
        Boost::boost
        Boost::program_options
        Boost::regex
        Boost::serialization
        Boost::filesystem
        Boost::thread
        Boost::timer
        Boost::chrono
        Boost::atomic
)

enable_testing()
add_test(NAME test_boost_compiled COMMAND test_boost_compiled --name ohos --count 3)
