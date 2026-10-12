# 使用

通过Conan安装sopt/5.0.1，启用CMakeDeps及CMakeToolchain。
`find_package(sopt CONFIG REQUIRED)`；`target_link_libraries(app PRIVATE sopt::sopt)`。
公开头文件位于include/sopt；TIFF和Eigen通过Conan传播给消费者。
本包只安装库、头文件、原始fixtures及许可，不安装示例CLI。
