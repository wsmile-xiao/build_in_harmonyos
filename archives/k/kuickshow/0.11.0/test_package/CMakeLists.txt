cmake_minimum_required(VERSION 3.16)
project(kuickshow_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)

# The consumer test drives the installed kuickshow binary (KS_TEST_BIN)
# and validates the packaged data (KS_TEST_DATA_DIR / KS_TEST_PREFIX);
# it only needs QtCore for file/string handling.
add_executable(kuickshow_consumer_test main.cpp)
target_link_libraries(kuickshow_consumer_test PRIVATE Qt6::Core)
