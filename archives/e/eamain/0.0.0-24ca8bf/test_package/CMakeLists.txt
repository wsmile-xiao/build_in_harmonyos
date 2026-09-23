cmake_minimum_required(VERSION 3.15)
project(test_eamain CXX)

# Find the package via Conan-generated CMakeDeps
find_package(EAMain REQUIRED)

# EAStdC requires user-provided debug operator new/delete (Config.h contract);
# the consumer side provides forwarding implementations (same approach as the
# eastdc/0.0.0-fbcc34e test_package).
add_library(ea_allocator STATIC ea_allocator_impl.cpp)

add_executable(test_eamain test.cpp)
target_link_libraries(test_eamain EAMain::EAMain ea_allocator)

enable_testing()
add_test(NAME test_eamain COMMAND test_eamain)
