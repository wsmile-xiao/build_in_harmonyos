cmake_minimum_required(VERSION 3.15)
project(test_sonnet CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Widgets)
find_package(KF6Sonnet 6.18.0 CONFIG REQUIRED)

add_executable(test_sonnet test.cpp)
target_link_libraries(test_sonnet PRIVATE KF6::SonnetCore KF6::SonnetUi Qt6::Widgets)
# Keep a literal $ORIGIN in the ELF RPATH so the OHOS loader searches beside
# the consumer executable, where test() stages the Conan shared libraries.
target_link_options(test_sonnet PRIVATE "-Wl,-rpath,\$ORIGIN" "-Wl,--disable-new-dtags")

enable_testing()
add_test(NAME test_sonnet COMMAND test_sonnet)
