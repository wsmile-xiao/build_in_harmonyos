cmake_minimum_required(VERSION 3.15)
project(test_aiksaurus CXX)

find_package(aiksaurus REQUIRED)

add_executable(test_aiksaurus test_aiksaurus.cpp)
target_link_libraries(test_aiksaurus aiksaurus::aiksaurus)

# Executable args (meanings.dat / words.dat) are supplied by
# test_package/conanfile.py via self.run(); no cmake add_test here.
