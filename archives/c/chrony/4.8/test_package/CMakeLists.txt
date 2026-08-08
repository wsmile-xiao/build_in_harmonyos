cmake_minimum_required(VERSION 3.15)
project(test_chrony C)

add_executable(test_chrony test.c)

# CHRONYC_PATH is injected by test_package/conanfile.py build() so test.c
# stats the Conan-packaged chronyc, not a host PATH lookup (R34).
if(NOT DEFINED CHRONYC_PATH)
    message(FATAL_ERROR "CHRONYC_PATH must be defined (Conan packaged chronyc path)")
endif()
target_compile_definitions(test_chrony PRIVATE CHRONYC_PATH="${CHRONYC_PATH}")

# No add_test(): test_chrony is cross-compiled for OHOS aarch64 and cannot
# be executed on the x86 CI worker (Exec format error). It is a
# compile-time verification target; runtime ELF checks live in conanfile.py.
