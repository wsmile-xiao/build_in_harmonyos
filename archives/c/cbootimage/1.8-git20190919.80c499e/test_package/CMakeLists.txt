cmake_minimum_required(VERSION 3.15)
project(test_cbootimage C)

# cbootimage is a standalone CLI tool: verify the binary exists in bin/
# and run it (without args) to check it produces the expected usage output.
add_test(
    NAME test_cbootimage_binary
    COMMAND sh -c "cbootimage 2>&1 | grep -q 'Usage: cbootimage'"
)