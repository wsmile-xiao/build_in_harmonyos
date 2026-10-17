# tng 1.8.2 — CMake 静态库以 PRIVATE 链接 zlib 时，Conan 静态包消费者链接报 undefined symbol（uncompress/compressBound/compress）

## 问题

tng 1.8.2（GROMACS TNG 轨迹 I/O 库，CMake 工程）以静态库（libtng_io.a）经 Conan
交付时，消费者（test_package）链接报：

```
ld.lld: error: undefined symbol: uncompress
>>> referenced by tng_io.c:(tng_block_read_next) in archive .../lib/libtng_io.a
ld.lld: error: undefined symbol: compressBound / compress
```

## 根因

上游 CMakeLists.txt 中，zlib 以 **PRIVATE** 方式链接到静态库目标：

```cmake
target_link_libraries(${NAME} ${_link_type} ZLIB::ZLIB)   # _link_type = PRIVATE
```

在**动态库**场景 PRIVATE 链接依赖不会泄漏给消费者（甚至不会写入 NEEDED 之外的元数据），
但**静态归档**场景下 zlib 的符号会被扇入 libtng_io.a，而链接 zlib 的链接行并不会出现在
归档自身的导出元数据中——Conan 打包静态库时若只用 `cpp_info.libs` 而不补充 zlib 传递链接，
消费者链接静态归档必然出现 zlib 符号未定义。

这是"CMake 静态库 PRIVATE 链接依赖不向消费者传播"的经典问题，
与本仓库 E247（pkg-config Libs.private 静态 C++ 运行时传播）同类不同触发面。

## 方案

利用上游自带的内部 zlib（external/zlib 目录）在**归档内部**自包含：

- 配方 `generate()` 设置 `TNG_BUILD_OWN_ZLIB=ON`
- 上游 CMake 在 OWN_ZLIB 分支把 `adler32.c ... zutil.c` 等 zlib 源文件作为 OBJECT
  库编入 libtng_io（`add_tng_io_library(tng_io OWN_ZLIB)`），归档不再引用外部 zlib 符号
- `package_info()` 无需 `system_libs` / 传递 requires，消费者零感知

## 验证

- 修复前：conan create 的 test_package 阶段链接 `libtng_io.a` 报
  `undefined symbol: uncompress/compressBound/compress`（G2 FAIL）
- 修复后：`ohc-run.py conan-verify tng 1.8.2` G2/G3/G4 全 PASS；
  独立消费者用例（consumer_test.c，仅用公开头 + libtng_io.a）编译链接运行 PASS（exit 0）

## 适用边界

- **适用**：上游以 `target_link_libraries(<static> PRIVATE ZLIB::ZLIB)`（或同类符号级
  依赖）链接 zlib 的 CMake 工程；以静态归档交付；上游自带内部 zlib 实现（external/zlib）
- **反例**：动态库交付（PRIVATE 不泄漏，无需处理）；上游无内部 zlib 时改用
  `requires("zlib/...")` + `cpp_info` 传递依赖；系统同名 libz 静态冲突属 E541 边界

## 查重差异

- E539：zlib test_package PIC 探测——触发面是静态归档链接 DSO 的 relocation（非 PIC 对象），不是符号缺失
- E277：autotools 配置期 vendored 依赖（Required library not found）——触发面是 configure 找不到依赖
- E247：pkg-config Libs.private 静态 C++ 运行时——触发面是 pkg-config 元数据，本候选是 CMake PRIVATE 链接
- 新增差异：CMake `PRIVATE ZLIB::ZLIB` 静态归档 + Conan 静态包 → 消费者 undefined symbol；
  方案为上游自带 zlib 开关（OWN_ZLIB）归档内自包含