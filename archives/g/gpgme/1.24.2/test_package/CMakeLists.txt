cmake_minimum_required(VERSION 3.21)
project(gpgme_consumer LANGUAGES C CXX)
find_package(libgpg-error CONFIG REQUIRED)
find_package(Qt6 CONFIG REQUIRED COMPONENTS Core)
find_package(Gpgmepp 1.24.2 CONFIG REQUIRED)
find_package(QGpgmeQt6 1.24.2 CONFIG REQUIRED)

# gpgme.h itself includes <gpg-error.h>, and Gpgmepp/QGpgme install their
# headers below versioned subdirectories, so each consumer declares the include
# roots it actually needs instead of relying on the imported targets'
# INTERFACE_INCLUDE_DIRECTORIES alone.
set(GPGME_INCLUDE_DIRS
    "${GPGME_PACKAGE_FOLDER}/include"
    "${GPGME_PACKAGE_FOLDER}/include/gpgme++"
    "${GPGME_PACKAGE_FOLDER}/include/qgpgme-qt6")

# Exercise the C API independently from the Gpgmepp/Qt6 consumer.
add_executable(gpgme_c_consumer test.c)
target_include_directories(gpgme_c_consumer PRIVATE "${GPGME_PACKAGE_FOLDER}/include")
target_link_directories(gpgme_c_consumer PRIVATE "${GPGME_PACKAGE_FOLDER}/lib")
target_link_libraries(gpgme_c_consumer PRIVATE gpgme libgpg-error::libgpg-error)

add_executable(gpgme_consumer test.cpp)
target_include_directories(gpgme_consumer PRIVATE ${GPGME_INCLUDE_DIRS})
target_link_libraries(gpgme_consumer PRIVATE Gpgmepp QGpgmeQt6 Qt6::Core libgpg-error::libgpg-error)
