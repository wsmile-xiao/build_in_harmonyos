cmake_minimum_required(VERSION 3.15)
project(qwinff_test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

find_package(Qt5 REQUIRED COMPONENTS Core Test Widgets Network)

# --- Upstream unit test #1: testversioncompare (src/tests/testversioncompare) ---
add_executable(testversioncompare
  testversioncompare/testversioncompare.cpp
  services/versioncompare.cpp)
target_include_directories(testversioncompare PRIVATE .)
target_link_libraries(testversioncompare Qt5::Test)

# --- Upstream unit test #2: testupdateinfoparser (src/tests/testupdateinfoparser) ---
add_executable(testupdateinfoparser
  testupdateinfoparser/testupdateinfoparser.cpp
  services/updateinfoparser.cpp
  services/xmllookuptable.cpp
  services/constants.cpp)
target_include_directories(testupdateinfoparser PRIVATE .)
# constants.h includes <QColor> (QtGui), so link Widgets like the main app does
target_link_libraries(testupdateinfoparser Qt5::Test Qt5::Widgets)

enable_testing()
add_test(NAME testversioncompare COMMAND testversioncompare)
add_test(NAME testupdateinfoparser COMMAND testupdateinfoparser)
