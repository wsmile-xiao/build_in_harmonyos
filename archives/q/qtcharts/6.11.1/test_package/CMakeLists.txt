cmake_minimum_required(VERSION 3.16)
project(test_qtcharts CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Gui Widgets)
# qtbase-gui and qtcharts are installed under separate Conan prefixes.  The
# umbrella Qt6 config only searches its own prefix for add-on modules, so find
# the Charts module's native config package directly.
find_package(Qt6Charts 6.11.1 CONFIG REQUIRED)
add_executable(test_qtcharts test_qtcharts.cpp)
target_compile_features(test_qtcharts PRIVATE cxx_std_17)
target_link_libraries(test_qtcharts PRIVATE Qt6::Charts)
