cmake_minimum_required(VERSION 3.15)
project(test_psyinf_gmtl CXX)

# GMTL is header-only: find_package only brings in the include path.
find_package(psyinf-gmtl REQUIRED)

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE psyinf-gmtl::psyinf-gmtl)
target_compile_features(consumer PRIVATE cxx_std_17)

# No enable_testing()/add_test() here on purpose: test_package/conanfile.py's
# test() executes ./consumer directly (through the cross-compiling emulator),
# so a registered-but-never-run CTest test would only invite drift between the
# two entry points.
