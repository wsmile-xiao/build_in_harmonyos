cmake_minimum_required(VERSION 3.16)
project(kwalletmanager_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)

# The consumer test drives the installed kwalletmanager5 binary
# (KWM_TEST_BIN) and validates the installed share/ metadata
# (KWM_TEST_SHARE_DIR); it only needs QtCore for process/file handling.
add_executable(kwalletmanager_consumer_test main.cpp)
target_link_libraries(kwalletmanager_consumer_test PRIVATE Qt6::Core)
