cmake_minimum_required(VERSION 3.16)
project(test_boost_morpheus_components LANGUAGES CXX)

find_package(Python 3.12 COMPONENTS Interpreter Development REQUIRED)
find_package(
    Boost 1.90.0 CONFIG REQUIRED
    COMPONENTS filesystem program_options system python312
)

add_executable(test_boost_morpheus_components test.cpp)
target_compile_features(test_boost_morpheus_components PRIVATE cxx_std_17)

set(_boost_test_python_library Python::Python)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    set(_boost_test_python_include_dirs ${Python_INCLUDE_DIRS})
    if(NOT _boost_test_python_include_dirs AND Python_INCLUDE_DIR)
        set(_boost_test_python_include_dirs "${Python_INCLUDE_DIR}")
    endif()
    if(_boost_test_python_include_dirs)
        target_include_directories(
            test_boost_morpheus_components
            PRIVATE ${_boost_test_python_include_dirs}
        )
    endif()

    set(_boost_test_python_library "${Python_LIBRARY}")
    if(NOT _boost_test_python_library AND Python_LIBRARIES)
        list(GET Python_LIBRARIES 0 _boost_test_python_library)
    endif()
    if(NOT _boost_test_python_library)
        message(FATAL_ERROR "Python library not found for OHOS Boost.Python test")
    endif()
endif()

target_link_libraries(
    test_boost_morpheus_components
    PRIVATE
        Boost::filesystem
        Boost::program_options
        Boost::system
        Boost::python312
        ${_boost_test_python_library}
)

if(IS_ABSOLUTE "${_boost_test_python_library}")
    get_filename_component(_boost_test_python_libdir "${_boost_test_python_library}" DIRECTORY)
    set_target_properties(
        test_boost_morpheus_components
        PROPERTIES BUILD_RPATH "${_boost_test_python_libdir}"
    )
endif()
