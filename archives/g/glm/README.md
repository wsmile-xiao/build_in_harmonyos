# glm

## 简介
GLM (OpenGL Mathematics) — header-only C++ 数学库，API 设计兼容 GLSL 着色器语言。提供向量、矩阵、四元数等图形学常用数学操作。

## OHOS 适配
- header-only 库，只需复制 glm 头文件目录到 `~/usr/local/include/glm`
- CMake 4.1.2 不支持 `cmake_minimum_required(VERSION 2.8)`，需修改 CMakeLists.txt
- 可跳过 CMake 直接手动安装头文件

## 依赖
- 编译依赖：无（header-only）
- 运行依赖：无

## 功能验证
```bash
# 编译测试
echo '#include <glm/glm.hpp>
int main() { glm::vec4 v(1,2,3,4); return 0; }' > test.cpp
clang++ -std=c++11 -I ~/usr/local/include test.cpp -o test && ./test && echo "OK"
```

## 参考
- GitHub：https://github.com/g-truc/glm
