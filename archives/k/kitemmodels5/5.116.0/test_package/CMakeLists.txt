cmake_minimum_required(VERSION 3.16)
project(test_kitemmodels5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Test)
find_package(KF5ItemModels 5.116.0 REQUIRED)

add_executable(test_kitemmodels5 test_kitemmodels5.cpp)
target_link_libraries(test_kitemmodels5 PRIVATE Qt5::Gui Qt5::Test KF5::ItemModels)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_kitemmodels5 PRIVATE
    KITEMMODELS_SO_PATH="$<TARGET_FILE:KF5::ItemModels>")

enable_testing()
add_test(NAME test_kitemmodels5 COMMAND test_kitemmodels5)
