# cppcmd 0.1.0 — packaging 说明

cppcmd 是 header-only C++ 库（无编译产物），Conan 配方
(conanfile.py) 以 `package_type=header-library` 直接分发公开头文件
(include/cppcmd/*.hpp)，无需预编译二进制包。

- 构建系统: CMake（上游 INTERFACE 库）
- 制品: 头文件 4 个（CommandInterpreter.hpp / Expression.hpp / Parser.hpp / Value.hpp）+ LICENSE
- 安装路径: include/ （Conan package folder）
- commands.json: 不适用（纯库包，无 CLI 可执行文件，R38/PF8）