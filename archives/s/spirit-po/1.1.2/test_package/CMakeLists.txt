cmake_minimum_required(VERSION 3.15)
project(spirit_po_consumer LANGUAGES CXX)

find_package(spirit-po CONFIG REQUIRED)

add_executable(test_spirit_po test_spirit_po.cpp)
target_compile_features(test_spirit_po PRIVATE cxx_std_11)
target_link_libraries(test_spirit_po PRIVATE spirit-po::spirit-po)
