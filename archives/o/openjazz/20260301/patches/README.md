# patches

本版本（openjazz 20260301）无源码补丁。

所有 OHOS 适配均通过配方层（conanfile.py 的 CMakeToolchain 变量）完成：
- `CMAKE_SYSTEM_NAME=Linux` 平台兼容（E092）
- `SDL_VERSION=2` 固定 SDL2 后端
- 无平台宏注入源码（R8）

对应 conandata.yml：`patches: {}`。
