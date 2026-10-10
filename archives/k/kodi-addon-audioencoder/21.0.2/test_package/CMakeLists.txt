cmake_minimum_required(VERSION 3.15)
project(test_audioencoder_wav LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-addon-audioencoder".
find_package(kodi-addon-audioencoder CONFIG REQUIRED)

add_executable(test_audioencoder_wav test_audioencoder_wav.cpp)
target_compile_features(test_audioencoder_wav PRIVATE cxx_std_17)
target_link_libraries(test_audioencoder_wav PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME audioencoder_wav_addon_entry_points
         COMMAND test_audioencoder_wav ${ADDON_LIB_DIR}/audioencoder.wav.so)
