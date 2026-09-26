cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(BitmapPlusPlus REQUIRED)

# 消费者测试：真实调用公开 API（构造/填充/索引/save/load/迭代）
add_executable(test_bitmapplusplus test_bitmapplusplus.cpp)
target_link_libraries(test_bitmapplusplus PRIVATE bmp::BitmapPlusPlus)
set_property(TARGET test_bitmapplusplus PROPERTY CXX_STANDARD 17)
set_property(TARGET test_bitmapplusplus PROPERTY CXX_STANDARD_REQUIRED ON)

# 鸿蒙特有测试：BMP 读写回环在 OHOS 运行时的真实行为
add_executable(test_bitmapplusplus_ohos test_bitmapplusplus_ohos.cpp)
target_link_libraries(test_bitmapplusplus_ohos PRIVATE bmp::BitmapPlusPlus)
set_property(TARGET test_bitmapplusplus_ohos PROPERTY CXX_STANDARD 17)
set_property(TARGET test_bitmapplusplus_ohos PROPERTY CXX_STANDARD_REQUIRED ON)