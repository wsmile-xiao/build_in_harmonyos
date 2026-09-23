cmake_minimum_required(VERSION 3.15)
project(test_modplug_ohos C)

# test_ohos builds its own consumer binary (R34: the source must
# substantively call the tested package's API) and runs it on-package
# against the OHOS-signed shared library, plus the seven
# ELF/musl/SONAME/NEEDED/codesign/host-path checks driven from
# conanfile.py test(). This directory is fully self-contained: the
# test source is test_modplug.c HERE (no ../test_package reference)
# and the MOD fixture is decoded next to the binary by conanfile.py
# test() before the run, so test_ohos still works if the directory is
# copied or executed on its own.
find_package(libmodplug REQUIRED)

add_executable(test_modplug test_modplug.c)
target_link_libraries(test_modplug PRIVATE libmodplug::libmodplug)
target_compile_features(test_modplug PRIVATE c_std_99)
