# TinyGLTFLoader

TinyGLTFLoader is a header-only C++ parser for glTF 1.x assets.

## 功能概述

- 解析 ASCII 和 binary glTF 1.x 资源
- 支持内嵌或外部 buffer，以及 PNG、JPEG、BMP 和 GIF 图像
- 仅依赖 C++ STL 与随源码提供的 picojson、stb_image 头文件

## OHOS 适配

- Conan 包安装 `tiny_gltf_loader.h`、`picojson.h` 和 `stb_image.h`，不产生动态库或静态库。
- 上游 Makefile 的 `-Wall -Werror` 会在 Clang 下将两处布尔表达式位运算警告视为错误；配方应用补丁，将其改为语义正确的逻辑与运算。
- `test_package` 直接编译并运行真实消费者，解析随测试提供的 glTF fixture。

## 依赖

无 Conan 运行时依赖。

## 参考

- [上游仓库](https://github.com/syoyo/tinygltfloader)
- [glTF 规范](https://www.khronos.org/gltf/)
