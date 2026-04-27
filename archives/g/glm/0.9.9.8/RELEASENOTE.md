# glm 0.9.9.8 Release Notes for HarmonyOS

## 版本信息

- **软件**: glm (OpenGL Mathematics Library)
- **版本**: 0.9.9.8
- **类型**: Header-only library
- **平台**: HarmonyOS/OpenHarmony (aarch64)

## 特性

glm 是一个头文件形式的 C++ 数学库，专为图形软件开发设计。主要特性包括：

- 矩阵和向量运算
- GLSL 风格的数学函数
- 仿射变换和投影变换
- 四元数操作
- 随机数生成
- 噪声函数

## 安装方法

### 使用预编译包

```bash
# 下载预编译包
cd glm-0.9.9.8-ohos-aarch64

# 运行安装脚本
PREFIX=$HOME/usr/local ./install.sh
```

### 手动安装

```bash
# 解压头文件
tar xzf glm-0.9.9.8-ohos-aarch64.tar.gz

# 复制到目标位置
cp -r storage/Users/currentUser/usr/local/include/glm $HOME/usr/local/include/
```

## 使用示例

```cpp
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <iostream>

int main() {
    glm::vec4 vec(1.0f, 0.0f, 0.0f, 1.0f);
    glm::mat4 trans = glm::mat4(1.0f);
    trans = glm::translate(trans, glm::vec3(1.0f, 1.0f, 0.0f));
    vec = trans * vec;
    std::cout << "glm test: " << vec.x << ", " << vec.y << ", " << vec.z << std::endl;
    return 0;
}
```

编译命令：

```bash
clang++ -std=c++11 -I$HOME/usr/local/include test.cpp -o test
```

## 编译说明

glm 是 header-only 库，无需编译二进制文件。本预编译包仅包含头文件。

## 平台适配

- **CMakeLists.txt 修改**: 将 `cmake_minimum_required(VERSION 3.2)` 改为 `VERSION 3.5`，以兼容 CMake 4.1.2
- **安装方式**: 手动复制头文件，绕过 CMake 平台检测问题

## 测试验证

- 编译测试程序成功
- glm 数学函数正常工作

## 已知问题

无已知问题。

## 更新日期

2026-04-27