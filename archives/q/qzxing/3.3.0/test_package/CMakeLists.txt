cmake_minimum_required(VERSION 3.10)
project(qzxing_probe CXX)

find_package(qzxing REQUIRED)
# qt5-qtbase CMakeDeps root config (declares Qt5::Core/Qt5::Gui targets;
# no per-module Qt5Core-config.cmake files are generated — see the recipe
# patch comment in src/CMakeLists.txt).
find_package(qt5-qtbase REQUIRED)

add_executable(qzxing_probe qzxing_probe.cpp)
target_link_libraries(qzxing_probe PRIVATE qzxing::qzxing)
