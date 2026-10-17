cmake_minimum_required(VERSION 3.15)
project(test_dhcp_helper C)

# dhcp-helper is a CLI daemon, not a library — there is nothing to link
# against. test_dhcp_helper receives the path of the installed dhcp-helper
# binary as argv[1] from test_package/conanfile.py test(), spawns it, and
# asserts its privilege-free argument paths. Testing is driven by Conan,
# not CTest.

add_executable(test_dhcp_helper test_dhcp_helper.c)
