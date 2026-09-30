cmake_minimum_required(VERSION 3.16)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Network)
# alkimia installs LibAlkimia6Config.cmake under lib/cmake; it is located
# through CMAKE_PREFIX_PATH (cmake_find_mode=none).
find_package(LibAlkimia6 8.2.1 REQUIRED)
# alkonlinequotesprofile.h includes <KSharedConfig>; headers of KF6Config are
# needed by consumers of AlkOnlineQuoteSource/Profile (LibAlkimia6Config pulls
# the target in via find_dependency, find it explicitly for clarity).
find_package(KF6Config REQUIRED)

add_executable(test_libalkimia test_libalkimia.cpp)
target_link_libraries(test_libalkimia PRIVATE Alkimia::alkimia Qt6::Core Qt6::Network KF6::ConfigCore)
