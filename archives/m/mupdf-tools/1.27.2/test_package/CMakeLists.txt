cmake_minimum_required(VERSION 3.15)
project(test_mupdf_tools C)

# L0c: test source file present (test.sh)
# The actual test runs mutool binary via conanfile.py test()

enable_testing()
add_test(NAME mupdf_tools_test COMMAND sh -c "mutool -v")
