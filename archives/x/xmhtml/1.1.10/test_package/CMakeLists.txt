cmake_minimum_required(VERSION 3.15)
project(xmhtml_consumer C)

# 配方 package_info() 声明了 cmake_file_name=XmHTML / cmake_target_name=XmHTML::XmHTML
find_package(XmHTML REQUIRED)

add_executable(test_xmhtml_consumer test_xmhtml_consumer.c)
target_link_libraries(test_xmhtml_consumer PRIVATE XmHTML::XmHTML)
