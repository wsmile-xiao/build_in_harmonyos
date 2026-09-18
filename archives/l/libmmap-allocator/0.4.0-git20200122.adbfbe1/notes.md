# libmmap-allocator 0.4.0-git20200122.adbfbe1 移植记录

## 上游与构建

- 上游仓库：`https://github.com/johannesthoma/mmap_allocator`
- 精确提交：`adbfbe165d9cc21c64c61f4d5133160cbd5c2d77`
- 构建入口：上游 Makefile
- 官方回归入口：`make test`
- 独立官方测试：`test_mmap_fixed.c`

## HarmonyOS 适配

上游 Makefile 的链接和测试目标直接调用 `g++`、`gcc`、`ar`，无法接收
Conan 注入的 HarmonyOS 工具链。`0001-Makefile.patch` 将这些调用改为
`$(CXX)`、`$(CC)`、`$(AR)`，为共享库补充 ELF SONAME，并将测试目标改为直接使用
`LD_LIBRARY_PATH=. ./test_allocator`，不依赖目标机 bash。

上游 `mmappable_vector` 直接使用 libstdc++ 的 `_M_impl`、`_M_deallocate`
和 `_M_get_Tp_allocator` 私有成员；HarmonyOS libc++ 没有这些成员。
`0002-mmap_allocator.h.patch` 让 allocator 副本共享映射配置，并对文件映射
的平凡类型跳过默认构造；`0003-mmappable_vector.h.patch` 改用公共
`std::vector` 操作完成扩容和释放，保留标准容器 API。

消费者测试通过 CMake 验证 Conan 生成的 `mmap_allocator::mmap_allocator`
目标；HarmonyOS 专测进一步验证运行时页大小宏、真实文件 mmap 和
`READ_WRITE_SHARED` 写回行为。

`test_mmap_fixed.c` 原样运行时可能因短映射后的 `MAP_FIXED` 扩展覆盖相邻
运行时区域而崩溃。`0004-test_mmap_fixed.c.patch` 在所有平台先预留完整的
4 MiB 重映射范围，再执行固定地址重映射，仍验证 `MAP_FIXED` 地址一致性。

补丁由 `scripts/ohc-run.py refresh-patch --auto` 生成；Windows 环境仅对
自动生成的文件头做路径规范化，以便 Conan 在不同工作目录应用。

## 已知边界

文件映射对象仍应使用平凡可默认构造的类型（上游测试使用 `int`）；配方统一
按 C++17 Clang 构建。交叉构建时 Conan 只执行编译和链接，完整上游测试及
HarmonyOS 专测通过 HDC 在 HarmonyOS 6.0 虚拟机上执行。
