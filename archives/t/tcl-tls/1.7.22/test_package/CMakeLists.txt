cmake_minimum_required(VERSION 3.15)
project(test_tcl_tls C)

# tcl-tls is a Tcl extension (.so loaded by Tcl runtime), not a standard C library.
# The test verifies the .so is a valid ELF shared library (dlopen not usable
# because objcopy strips ELF signature on OHOS).
add_executable(test_tcl_tls test.c)
