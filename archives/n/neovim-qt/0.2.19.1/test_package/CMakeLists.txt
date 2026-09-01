cmake_minimum_required(VERSION 3.16)
project(test_neovim_qt CXX)

# neovim-qt 是 Qt5 GUI 应用（libneovim-qt + nvim-qt），无独立库目标；
# 消费者测试链接 Qt5（qtbase 包提供的 Qt5Config 聚合配置）验证
# Qt5Widgets/Qt5Network 可链接，并运行 nvim-qt --version 验证应用可执行。
find_package(QT NAMES Qt5 COMPONENTS Core Network Widgets REQUIRED)
find_package(Qt5 COMPONENTS Core Network Widgets REQUIRED)

add_executable(test_neovim_qt test.cpp)
target_link_libraries(test_neovim_qt PRIVATE Qt5::Core Qt5::Network Qt5::Widgets)

enable_testing()
add_test(NAME test_neovim_qt COMMAND test_neovim_qt)
