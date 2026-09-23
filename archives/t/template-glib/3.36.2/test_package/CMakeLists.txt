cmake_minimum_required(VERSION 3.15)
# Find template-glib via Conan-generated CMakeDeps.
find_package(template-glib REQUIRED)

add_executable(test_tmpl test_tmpl.c)
target_link_libraries(test_tmpl template-glib::template-glib)

enable_testing()
add_test(NAME test_tmpl COMMAND test_tmpl)
