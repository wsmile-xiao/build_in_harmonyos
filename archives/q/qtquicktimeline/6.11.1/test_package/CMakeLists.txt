cmake_minimum_required(VERSION 3.16)
project(test_qtquicktimeline CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Gui Qml)
# qtbase and qtquicktimeline are installed under separate Conan prefixes.  The
# umbrella Qt6 config only searches its own prefix for add-on modules, so find
# the QuickTimeline module's native config package directly.
find_package(Qt6QuickTimeline 6.11.1 CONFIG REQUIRED)
add_executable(test_qtquicktimeline test_qtquicktimeline.cpp)
target_compile_features(test_qtquicktimeline PRIVATE cxx_std_17)
target_link_libraries(test_qtquicktimeline PRIVATE Qt6::QuickTimeline Qt6::Qml Qt6::Gui Qt6::Core)
