cmake_minimum_required(VERSION 3.15)
project(libcdio_paranoia_test LANGUAGES C)

find_package(libcdio-paranoia CONFIG REQUIRED)

add_executable(libcdio_paranoia_test test.c)
target_link_libraries(libcdio_paranoia_test PRIVATE libcdio-paranoia::libcdio-paranoia)

# Older published libcdio/2.3.0 metadata has an empty CMake include-dir
# property even though the package contains include/cdio/*.h.  The paranoia
# public headers include those dependency headers, so supply the package folder
# as a consumer-side compatibility fallback.
if(DEFINED libcdio_PACKAGE_FOLDER_RELEASE)
    target_include_directories(
        libcdio_paranoia_test PRIVATE
        "${libcdio_PACKAGE_FOLDER_RELEASE}/include"
    )
endif()
