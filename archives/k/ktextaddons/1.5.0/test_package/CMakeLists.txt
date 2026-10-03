cmake_minimum_required(VERSION 3.15)
project(test_ktextaddons CXX)

# KF6<TextAddon> config files chain through Qt6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6TextUtils REQUIRED)
find_package(KF6TextAddonsWidgets REQUIRED)

add_executable(test_ktextaddons test.cpp)
target_link_libraries(test_ktextaddons
    KF6::TextUtils
    KF6::TextAddonsWidgets
    # KF6TextAddonsWidgets links Qt6::Widgets PRIVATEly, so the include
    # paths do not propagate; link Qt6::Widgets directly for the QWidget
    # usage in the smoke test.
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
)

set_target_properties(test_ktextaddons PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME test_ktextaddons COMMAND test_ktextaddons)
