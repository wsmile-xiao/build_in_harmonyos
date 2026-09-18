cmake_minimum_required(VERSION 3.13)
project(latino_embed_test C)

# CMakeDeps (test_package conanfile) provides the latino target; the
# transitive readline headers are exported through it because the recipe
# declares cpp_info.requires = readline::readline (latcompat.h includes
# <readline/history.h> in the __linux__ branch).
find_package(latino REQUIRED)

add_executable(latino_embed_test latino_embed_test.c)
target_link_libraries(latino_embed_test PRIVATE latino::latino)
