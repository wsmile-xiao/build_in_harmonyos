# DRAFT — json-parser 1.1.0：包内同时含 .a/.so 时 CMakeDeps 误选 .so 导致消费者运行期 symbol not found

## 问题

`conan create` 通过后，test_package 运行测试二进制报：

```
Error loading shared library libjsonparser.so.1.0: (needed by .../test_json-parser)
Error relocating ...: json_parse: symbol not found
```

即：消费者（test_package）链接阶段选用了共享库，运行期又加载到不匹配/陈旧的
`.so.1.0`，符号重定位失败。

## 根因

json-parser 的 Makefile 无条件同时产出并安装 `libjsonparser.a` 与
`libjsonparser.so`（soname `.1.0`）。Conan CMakeDeps 生成 target 时，
`find_library(NAMES jsonparser PATHS <pkg>/lib)` 在 .a/.so 并存时按 find_library
查找顺序**选中了 .so**，于是：

1. 链接命令写的是 `.../p/lib/libjsonparser.so`（而非 .a），二进制的
   NEEDED 变成 `libjsonparser.so.1.0`；
2. 运行期 conanrun 环境搜索 lib 目录，若 conan 缓存里残留**旧/坏**的
   `libjsonparser.so.1.0`（前几次失败构建遗留在其他 build 目录），加载的是
   旧文件，符号对不上 → `symbol not found`。

即便配方默认 `shared=False`（LIBRARY_TYPE 也标 STATIC），只要包目录里 .a/.so
都存在，CMakeDeps 的 find_library 仍可能取到 .so。这是"一种库同时打包两种形态"
与"CMakeDeps 静态/共享选择依赖文件存在性"的交互问题。

## 方案

配方 `package()` 中按 shared 选项只保留一种库形态（默认 shared=False 只留
静态库），并清理 conan 缓存中该库的陈旧包：

```python
def package(self):
    autotools.install(args=["-j1"])
    libdir = os.path.join(self.package_folder, "lib")
    if os.path.isdir(libdir):
        for name in os.listdir(libdir):
            if name.startswith("libjsonparser.so") and not self.options.shared:
                os.unlink(os.path.join(libdir, name))
            elif name == "libjsonparser.a" and self.options.shared:
                os.unlink(os.path.join(libdir, name))
```

前置：`conan remove "<pkg>/*" -c` 清理陈旧本地包缓存，避免运行期加载旧 .so。

## 验证

- 修复前：test_package 运行报 `Error loading shared library libjsonparser.so.1.0`
  + `symbol not found`；
- 修复后：包内仅 .a，CMakeDeps 链接静态库，test_package 运行通过，
  W3（build_and_test.sh）L0-L5 全过。

## 适用边界

- 适用于 Makefile 无条件同时产出并安装 .a/.so、且配方 options.shared 默认
  False（静态）的库；
- 适用于以静态库为交付主体、但构建系统又强制产出 .so 的场景。

## 反例 / 限制

- 若共享库是交付主体（shared=True 默认）或包方需要双形态共存，应显式用
  `cpp_info.set_property("cmake_file_name"/"cmake_target_name")` 或组件方式
  声明，而不是删除 .so；
- 删除文件仅影响 package 目录（conan 缓存制品），不影响源码与配方可复现性；
  重跑 conan create 会重新安装两种库再按选项筛选，结果稳定。

## 查重差异

- E073（HMDFS 对 .so 符号链接运行期加载不完整 → configure-static-only）根因是
  文件系统符号链接语义，本候选根因是 **CMakeDeps find_library 双形态选择**，
  发生阶段（链接/打包 vs 运行期加载）与方案（按选项过滤包内库形态 vs 静态编译）
  均不同，非等价；
- E004（musl BIND_NOW 加载 symbol not found）为 musl 链接标志问题，与本候选无关；
- 官方图库与草稿区均无"CMakeDeps 在 .a/.so 并存时误选 .so"条目，等价命中不存在。