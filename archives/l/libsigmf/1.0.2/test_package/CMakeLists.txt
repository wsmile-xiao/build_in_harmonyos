cmake_minimum_required(VERSION 3.15)
project(test_libsigmf CXX)

find_package(libsigmf REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(flatbuffers REQUIRED)

add_executable(test_libsigmf test_libsigmf.cpp)
target_link_libraries(test_libsigmf
  libsigmf::libsigmf
  nlohmann_json::nlohmann_json
  flatbuffers::flatbuffers)
set_target_properties(test_libsigmf PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_libsigmf COMMAND test_libsigmf)
