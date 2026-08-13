cmake_minimum_required(VERSION 3.15)
project(test_mailio CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# mailio 传递依赖 Boost 和 OpenSSL 头文件
find_package(mailio REQUIRED)
find_package(Boost REQUIRED)

add_executable(test_mailio test.cpp)
target_link_libraries(test_mailio mailio::mailio Boost::headers)

# 临时方案：CMakeDeps 将 boost INCLUDE_DIRS 设为空字符串。
# 使用包文件夹变量手动添加 include 目录（兼容 Release/Debug 等配置）。
foreach(_cfg RELEASE DEBUG RELWITHDEBINFO MINSIZEREL)
    if(DEFINED boost_PACKAGE_FOLDER_${_cfg})
        target_include_directories(test_mailio PRIVATE ${boost_PACKAGE_FOLDER_${_cfg}}/include)
    endif()
endforeach()
