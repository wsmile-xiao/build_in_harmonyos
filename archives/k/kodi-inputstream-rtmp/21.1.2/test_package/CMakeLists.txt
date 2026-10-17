cmake_minimum_required(VERSION 3.15)
project(test_inputstream_rtmp LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream consumer of the
# packaged add-on module.
find_package(kodi-inputstream-rtmp CONFIG REQUIRED)

add_executable(test_inputstream_rtmp test_inputstream_rtmp.cpp)
target_compile_features(test_inputstream_rtmp PRIVATE cxx_std_17)
target_link_libraries(test_inputstream_rtmp PRIVATE
                      kodi-inputstream-rtmp::kodi-inputstream-rtmp)

enable_testing()
add_test(NAME test_inputstream_rtmp COMMAND test_inputstream_rtmp)
