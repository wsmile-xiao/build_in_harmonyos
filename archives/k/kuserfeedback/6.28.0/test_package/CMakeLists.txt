cmake_minimum_required(VERSION 3.15)
project(test_kuserfeedback CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Network)
find_package(KF6UserFeedback REQUIRED)

add_executable(test_kuserfeedback test.cpp)
target_link_libraries(test_kuserfeedback KF6::UserFeedbackCore Qt6::Core Qt6::Network)
