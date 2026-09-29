cmake_minimum_required(VERSION 3.15)
project(test_kddockwidgets LANGUAGES CXX)

# Consumer test for kddockwidgets (R34: real API usage, no stub test).
# The 12 test cases in test.cpp (declared in test_package/MANIFEST.yml) run a
# real QtWidgets docking scenario offscreen through a case executor (per-case
# TEST PASS/FAIL output + SUMMARY + non-zero exit on failure) and are
# deterministic on both desktop sessions and headless OHOS devices. Every
# case's asserted behavior was verified against the upstream 2.4.0 sources
# (DockRegistry registers at ctor; title() defaults to uniqueName;
# isFloating() semantics; LayoutSaver restores into existing widgets matched
# by uniqueName):
#   1. MainWindow::uniqueName() round-trips the construction name
#   2. DockRegistry counts both dock widgets (ctor registration)
#   3. DockWidget::title() defaults to the construction uniqueName
#   4. setTitle() updates title()
#   5. second dock widget's title() is intact
#   6. dock widgets are not floating after addDockWidget() (dock1)
#   7. dock widgets are not floating after addDockWidget() (dock2)
#   8. LayoutSaver::saveToFile() succeeds
#   9. closing a docked dock widget hides it
#  10. LayoutSaver::restoreFromFile() succeeds
#  11. restore re-docks the closed dock widget (visible again)
#  12. restored dock widget is not floating

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KDDockWidgets REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(test_kddockwidgets test.cpp)
target_link_libraries(test_kddockwidgets KDAB::kddockwidgets Qt5::Widgets)

enable_testing()
add_test(NAME test_kddockwidgets COMMAND test_kddockwidgets)
