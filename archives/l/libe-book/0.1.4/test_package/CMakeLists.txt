cmake_minimum_required(VERSION 3.15)
project(test_libe_book CXX)

# libe-book's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both.
find_package(libe-book REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libe_book test_libe_book.cpp)
target_link_libraries(test_libe_book PRIVATE libe-book::libe-book librevenge::librevenge)

enable_testing()
add_test(NAME test_libe_book COMMAND test_libe_book)
