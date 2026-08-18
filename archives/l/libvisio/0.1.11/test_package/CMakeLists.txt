cmake_minimum_required(VERSION 3.15)
project(test_libvisio CXX)

# C++17 required by libvisio (AX_CXX_COMPILE_STDCXX([17]))
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(libvisio REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libvisio test.cpp)
target_link_libraries(test_libvisio libvisio::libvisio librevenge::librevenge)

# Workaround: librevenge package doesn't expose includedirs in cpp_info
# Add the include path manually using the package folder variable
# Support all build types (Release, Debug, RelWithDebInfo, MinSizeRel)
foreach(_config RELEASE DEBUG RELWITHDEBINFO MINSIZEREL)
    if(DEFINED librevenge_PACKAGE_FOLDER_${_config})
        target_include_directories(test_libvisio PRIVATE
            ${librevenge_PACKAGE_FOLDER_${_config}}/include/librevenge-0.0)
    endif()
endforeach()

enable_testing()
add_test(NAME test_libvisio COMMAND test_libvisio)
