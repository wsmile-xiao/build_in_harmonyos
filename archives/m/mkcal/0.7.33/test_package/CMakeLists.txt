cmake_minimum_required(VERSION 3.16)
project(test_mkcal CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6, and KCalendarCore (kcalendarcore installs KF6CalendarCoreConfig.cmake)
# come from the Conan dependencies; libmkcal-qt6.pc only describes the mkcal
# payload itself.
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6CalendarCore REQUIRED)

find_package(PkgConfig REQUIRED)
pkg_check_modules(MKCAL REQUIRED IMPORTED_TARGET libmkcal-qt6)

add_executable(test_mkcal test_mkcal.cpp)
target_link_libraries(test_mkcal PRIVATE Qt6::Core KF6::CalendarCore PkgConfig::MKCAL)

enable_testing()
add_test(NAME test_mkcal COMMAND test_mkcal)
