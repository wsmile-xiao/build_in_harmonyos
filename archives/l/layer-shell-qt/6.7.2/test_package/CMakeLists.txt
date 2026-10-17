cmake_minimum_required(VERSION 3.16)
project(test_layershellqt CXX)

find_package(LayerShellQt REQUIRED)

add_executable(test_layershellqt test.cpp)
# The project's installed LayerShellQtConfig.cmake exports the Interface
# library target as LayerShellQt::Interface (libLayerShellQtInterface.so).
target_link_libraries(test_layershellqt LayerShellQt::Interface)

enable_testing()
add_test(NAME test_layershellqt COMMAND test_layershellqt)
