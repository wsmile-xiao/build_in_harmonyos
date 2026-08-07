# netcdf 4.9.3 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libnetcdf.so 等 1 个库，供链接与 dlopen。

## 关键适配

本包打了 3 个补丁。三者都**只在鸿蒙/conan 组合下才发作**，上游在 glibc + 系统装 hdf5
的环境里一直是绿的。

### 1. `netcdf-0001-avoid-imported-target-in-try-compile.patch`

上游 `cmake/dependencies.cmake` 写 `set(CMAKE_REQUIRED_LIBRARIES HDF5::HDF5)` 后调
`check_symbol_exists`。后者内部走 `try_compile`，生成的是一个**独立临时工程**，
那里看不到调用方的 imported target，直接报

    Target "cmTC_xxxxx" links to: HDF5::HDF5 but the target was not found.

改用裸库名 `hdf5`，链接搜索路径由 `-L` 提供（配方以 `--inject-dep-libdirs` 注入）。

### 2. `netcdf-0002-alias-hdf5-target.patch`

conan 的 CMakeDeps 只声明**一个扁平目标** `hdf5::hdf5`（其 `cpp_info.libs` 由
`collect_libs()` 收全，已包含 `libhdf5_hl`），而上游按 FindHDF5 的惯例分别写
`HDF5::HDF5`（11 处）与 `hdf5::hdf5_hl`（4 处）。CMake 目标名大小写敏感，链接期报
`links to: HDF5::HDF5 but the target was not found`。

在 `find_package(HDF5)` **之后**一次补齐两个别名，覆盖后续所有引用点。
IMPORTED 目标默认只在创建它的目录可见，`ALIAS` 前须先 `IMPORTED_GLOBAL TRUE`。

> 为什么不用生成器的 `--cmake-alias-target`：那个功能在 `project()` **之前**建别名，
> 而那时 `find_package(hdf5)` 还没跑、`hdf5::hdf5` 尚不存在，`if(TARGET ...)` 判假，
> 别名根本没建出来（实撞）。它适用于目标在 `project()` 时就已存在的场景。

### 3. `netcdf-0003-link-libxml2.patch` —— 上游真 bug

上游对 libxml2 只调用了 `target_include_directories`，**从头到尾没有
`target_link_libraries`**，而 `libnetcdf.so` 确实引用了 `xmlReadMemory` /
`xmlCleanupParser` 等符号。

glibc 平台默认允许共享库留未定义符号（运行期再解析），所以上游 CI 发现不了；
OHOS 默认带 `--no-allow-shlib-undefined`，链接期直接报一串 undefined reference。

> 试过 `--extra-ldflags=-lxml2`，**无效**：它进的是 `CMAKE_*_LINKER_FLAGS`，
> 位置在目标文件**之前**，而链接器从左到右解析未定义符号，等于没加。
> 必须改上游的 `target_link_libraries` 才落在正确位置。

## 依赖说明

- **zlib 跟 hdf5 走**：`hdf5/1.14.6` 钉的是 `zlib/1.3.1.1`，写 `1.3.1` 会在图里冲突。
- **用 `curl/8.15.0` 而非 `libcurl/8.5.0`**：后者的 `validate()` 读
  `openssl.options.no_des`，而已发布的 `openssl/3.5.6` 没有任何 options，
  直接报 `option 'no_des' doesn't exist`。这是制品仓里既有的不兼容，
  **会卡住任何依赖 libcurl 的新包**，非本包引入。
- **libxml2 必须显式声明**：netcdf 自行判定 "XML Parser: libxml2" 并使用其头文件，
  不声明就没有头。注意它按 `<libxml2/libxml/parser.h>` 引用，需要 `include/` 的
  **上一层**在搜索路径里，由 `--inject-dep-includes` 保证。

## 选项取舍

依赖（libcurl/libxml2/zstd/zlib/hdf5/libaec）全部已在架，故 **DAP、NCZARR、
远程访问等真功能一个都没关**，只关了示例程序与上游测试（不进制品，
验收以本包 test_package 为准）。

⚠️ netcdf-c 4.9.3 把选项名统一加了 `NETCDF_ENABLE_` 前缀，旧名（`ENABLE_DAP` 等）
已废弃并告警。

## 状态

built（真机 conan create + test_package 通过）
