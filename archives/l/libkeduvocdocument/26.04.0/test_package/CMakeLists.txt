cmake_minimum_required(VERSION 3.16)
project(test_libkeduvocdocument CXX)

# The package ships its own LibKEduVocDocumentConfig.cmake (CMakeDeps is
# configured with cmake_find_mode=none so it does not shadow it).  Its
# installed target LibKEduVocDocumentImport__KEduVocDocument has
# INTERFACE_LINK_LIBRARIES "Qt6::Xml", so Qt6 must be found first.
find_package(Qt6 REQUIRED COMPONENTS Core Xml)
find_package(LibKEduVocDocument REQUIRED)

add_executable(test_libkeduvocdocument test.cpp)
target_link_libraries(test_libkeduvocdocument
    ${LIBKEDUVOCDOCUMENT_LIBRARIES}
    Qt6::Core
    Qt6::Xml
)
