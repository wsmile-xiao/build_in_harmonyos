cmake_minimum_required(VERSION 3.16)
project(test_qscintilla2 CXX)

find_package(Qt6 REQUIRED CONFIG COMPONENTS Widgets)

add_executable(test_qscintilla2 test_qscintilla2.cpp)
target_include_directories(test_qscintilla2 PRIVATE ${QSCINTILLA_INCLUDE_DIR})
target_link_directories(test_qscintilla2 PRIVATE ${QSCINTILLA_LIBRARY_DIR})
target_link_libraries(test_qscintilla2 PRIVATE qscintilla2_qt6 Qt6::Widgets)
target_compile_features(test_qscintilla2 PRIVATE cxx_std_17)
