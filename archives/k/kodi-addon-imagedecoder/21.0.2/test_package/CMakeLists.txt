cmake_minimum_required(VERSION 3.15)
project(test_imagedecoder_mpo LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-addon-imagedecoder".
find_package(kodi-addon-imagedecoder CONFIG REQUIRED)

add_executable(test_imagedecoder_mpo test_imagedecoder_mpo.cpp)
target_compile_features(test_imagedecoder_mpo PRIVATE cxx_std_17)
target_link_libraries(test_imagedecoder_mpo PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME imagedecoder_mpo_addon_entry_points
         COMMAND test_imagedecoder_mpo ${ADDON_LIB_DIR}/imagedecoder.mpo.so)
