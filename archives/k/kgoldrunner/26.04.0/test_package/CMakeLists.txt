cmake_minimum_required(VERSION 3.16)
project(kgoldrunner_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)

# The consumer test drives the installed kgoldrunner binary (KGR_TEST_BIN)
# and parses the packaged gamedata (KGR_TEST_DATA_DIR); it only needs
# QtCore for file/string handling.
add_executable(kgoldrunner_consumer_test main.cpp)
target_link_libraries(kgoldrunner_consumer_test PRIVATE Qt6::Core)
