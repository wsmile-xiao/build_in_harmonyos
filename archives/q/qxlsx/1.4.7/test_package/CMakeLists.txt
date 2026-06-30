cmake_minimum_required(VERSION 3.15)
project(test_QXlsx CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the QXlsx package via Conan-generated CMakeDeps
find_package(QXlsx REQUIRED)

# Qt5 include paths: needed for QXlsx headers that include Qt classes
# The Qt5 Conan wrapper provides libs but CMakeDeps only generates Qt5::Core
set(QT5_INCLUDE_DIR "/storage/Users/currentUser/usr/local/Qt5/include")
set(QT5_LIB_DIR "/storage/Users/currentUser/usr/local/Qt5/lib")

add_executable(test_QXlsx test.cpp)

# Link QXlsx (provides QXlsxQt5 static lib + its transitive deps via Conan)
target_link_libraries(test_QXlsx QXlsx::QXlsxQt5)

# Add Qt5 include paths and libs directly
target_include_directories(test_QXlsx PRIVATE
    ${QT5_INCLUDE_DIR}
    ${QT5_INCLUDE_DIR}/QtCore
    ${QT5_INCLUDE_DIR}/QtGui
    ${QT5_INCLUDE_DIR}/QtGui/5.15.2/QtGui/private
)
target_link_directories(test_QXlsx PRIVATE ${QT5_LIB_DIR})
target_link_libraries(test_QXlsx Qt5Core Qt5Gui)

enable_testing()
add_test(NAME test_QXlsx COMMAND test_QXlsx)
