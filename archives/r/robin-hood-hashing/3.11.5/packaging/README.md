# Packaging

robin-hood-hashing 3.11.5 为 header-only 库，无二进制产物：打包内容即
conan create 安装的头文件（include/robin_hood.h）与许可证（licenses/LICENSE）。
制品由 Conan 流水线（conan create + upload）产出，此处不重复存放二进制。
