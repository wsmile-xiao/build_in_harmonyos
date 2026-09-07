cmake_minimum_required(VERSION 3.15)
project(test_micro_inetd C)

# micro_inetd is a CLI tool, not a library — there is nothing to link
# against. test_micro_inetd receives the path of the installed micro_inetd
# binary as argv[1] from test_package/conanfile.py test(), forks it on an
# ephemeral loopback port, and drives the socket→stdin/stdout contract of
# the services it spawns (svc_cat / svc_exit42 built here as fixtures).
# Testing is driven by Conan, not CTest.
add_executable(test_micro_inetd test_micro_inetd.c)
add_executable(svc_cat svc_cat.c)
add_executable(svc_exit42 svc_exit42.c)
