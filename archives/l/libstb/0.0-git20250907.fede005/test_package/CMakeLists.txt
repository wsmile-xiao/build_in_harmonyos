cmake_minimum_required(VERSION 3.15)
project(test_libstb C)

find_package(libstb REQUIRED CONFIG)

# 消费者测试 1：多组件 API 断言（image/ds/sprintf/rect_pack/divide）
add_executable(test_libstb test_libstb.c)
target_link_libraries(test_libstb PRIVATE libstb::libstb)

# 消费者测试 2：终端用户图像管线（生成→PNG 编码→解码→resize2 放大→校验）
add_executable(consumer_image_pipeline consumer_image_pipeline.c)
target_link_libraries(consumer_image_pipeline PRIVATE libstb::libstb)

enable_testing()
add_test(NAME test_libstb COMMAND test_libstb)
add_test(NAME consumer_image_pipeline COMMAND consumer_image_pipeline)
