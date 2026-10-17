cmake_minimum_required(VERSION 3.15)
project(test_libportal_gtk4 C)

find_package(libportal-gtk4 REQUIRED)

add_executable(test_libportal_gtk4 test_libportal_gtk4.c)
target_link_libraries(test_libportal_gtk4 PRIVATE libportal-gtk4::libportal-gtk4)

# 鸿蒙特有消费者端到端用例：真实 session bus + mock portal 后端 +
# libportal-gtk4 公开 API 全链路往返（见 test_portal_e2e.c 头注）
add_executable(test_portal_e2e test_portal_e2e.c)
target_link_libraries(test_portal_e2e PRIVATE libportal-gtk4::libportal-gtk4)
