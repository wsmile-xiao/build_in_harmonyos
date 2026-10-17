# foonathan/memory

foonathan/memory 是一个提供 RawAllocator、内存池、内存栈及 STL 适配器的 C++ 内存分配库。

## 功能

- heap、new、malloc、static、virtual memory 等底层分配器
- memory stack、memory pool、memory arena 和临时分配器
- `std_allocator`、智能指针和 memory resource 适配器
- `nodesize_dbg` 容器节点大小辅助工具

## OHOS 适配

- 上游 CMake 仅按 `UNIX`/`WIN32` 选择安装目录；配方补丁同时识别 `HarmonyOS` 和 `OpenHarmony`。
- POSIX hosted 平台（包括 OHOS）上的 `malloc`/`operator new` 对小块分配可能不满足 `std::max_align_t`，配方补丁在三个默认分配器中使用 `posix_memalign`；Windows 保留原生分配路径。
- 构建时开启官方 CTest、关闭示例；`nodesize_dbg` 在本机生成容器节点大小头文件并随包安装。

## 依赖

无第三方编译依赖。构建测试阶段使用上游固定版本的 Catch2 单头文件下载。

## 参考

- 上游仓库：[foonathan/memory](https://github.com/foonathan/memory)
- 版本归档：`foonathan-memory/0.7`
