cmake_minimum_required(VERSION 3.16)
project(test_abseil LANGUAGES CXX)

find_package(absl CONFIG REQUIRED)

add_executable(test_abseil test.cpp)
target_compile_features(test_abseil PRIVATE cxx_std_17)
target_link_libraries(
  test_abseil
  PRIVATE
    absl::flat_hash_map
    absl::statusor
    absl::strings
)

enable_testing()
add_test(NAME abseil_consumer_api COMMAND test_abseil)
