cmake_minimum_required(VERSION 3.20)
project(test_kdeclarative LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Declarative REQUIRED CONFIG)

# The consumer test subclasses CalendarEventsPlugin (Q_OBJECT), so moc must
# run over the .cpp (test_kdeclarative.moc include at the bottom).
set(CMAKE_AUTOMOC ON)

add_executable(test_kdeclarative test_kdeclarative.cpp)
target_link_libraries(test_kdeclarative PRIVATE
    Qt6::Core
    Qt6::Gui
    KF6::CalendarEvents
)

enable_testing()
add_test(NAME test_kdeclarative COMMAND test_kdeclarative)
