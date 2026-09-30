cmake_minimum_required(VERSION 3.15)
project(test_kylinai C)

find_package(JsonCpp REQUIRED)

add_executable(test_kylinai test_kylinai.c)
target_compile_definitions(test_kylinai PRIVATE
    KYLIN_PLUGIN_DIR="${KYLIN_PLUGIN_DIR}"
)
# Linking jsoncpp into the harness puts Json:: symbols in the global
# scope at startup (what the real engine-loader host provides).
target_link_libraries(test_kylinai JsonCpp::JsonCpp)
