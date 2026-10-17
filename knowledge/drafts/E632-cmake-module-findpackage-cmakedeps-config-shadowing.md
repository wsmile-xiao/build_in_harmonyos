# E632 CMake 模块模式 find_package 被 CMakeDeps config 抢跑：变量空、target 缺失，预设 cache 变量 + cmake_find_mode=none 双修

## 问题现象

上游 CMake 项目按「Find 模块」惯例消费依赖（libminc 2.5.0 实撞）：

```cmake
find_package(ZLIB REQUIRED)                        # 用 ${ZLIB_LIBRARY}、ZLIB::ZLIB target
set(HDF5_NO_FIND_PACKAGE_CONFIG_FILE ON)
find_package(HDF5 REQUIRED COMPONENTS C)           # 用 ${HDF5_INCLUDE_DIRS}、${HDF5_LIBRARY}
find_package(NETCDF REQUIRED)                      # 上游自带 FindNETCDF.cmake：find_path/find_library
```

Conan 配方正常声明 `requires("hdf5/…")` 并走 `CMakeToolchain + CMakeDeps` 后，
configure 可能**不报错**（尤其上游对 find 结果只做宽松判断时），但编译期以
`fatal error: 'hdf5.h' file not found`、`undefined reference to H5Fopen`、
`Target "ZLIB::ZLIB" not found`（configure 期）等形态爆开。

## 根因

1. 本仓 Conan 2.29 的 `CMakeToolchain` 恒定写 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`
   （`generators/conan_toolchain.cmake`）。`find_package(HDF5)` 在 config 模式下
   按小写文件名命中 CMakeDeps 生成的 `hdf5-config.cmake`，**模块 FindHDF5 根本不执行**
   （上游显式 `HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON` 只关 FindHDF5 模块内部的
   config 分支，挡不住 PREFER_CONFIG 的全局抢跑）。
2. CMakeDeps 的 config 文件只定义 `hdf5::hdf5` 这类扁平 target 与 `hdf5_INCLUDE_DIRS`
   （小写）变量；上游要消费的 `HDF5_INCLUDE_DIRS/HDF5_LIBRARY`（大写）与
   `ZLIB::ZLIB`/`FindNETCDF` 的 `NETCDF_INCLUDE_DIR/NETCDF_LIBRARY` 无人定义。
   `ZLIB::ZLIB` target 只有 CMake 自带 FindZLIB 模块会创建（config 模式只有
   `zlib::zlib`）。这与 libmatio（thirdParties.cmake 打 hdf5::hdf5 分支补丁）、
   netcdf（hdf5 变量形态）先例同族。

## 修复步骤（双保险，libminc/2.5.0 配方实测）

1. `generate()` 里对三个依赖阻断 config 生成，让 find_package 全部回落模块模式：

   ```python
   for dep_name in ("zlib", "hdf5", "netcdf"):
       self.dependencies[dep_name].cpp_info.set_property("cmake_find_mode", "none")
   ```

   （`cmake_find_mode` 是 cpp_info 属性；`ConanFileInterface` 顶层无 `set_property`，
   直接照 `self.dependencies[x].set_property(...)` 写会 AttributeError——Conan 2.29 实测。）

   ⚠️ 这只挡 **CMakeDeps 自己的 config**；设备上已安装的第三方 config 包
   （harmonybrew 的 `lib/cmake/ZLIB/`）仍会被 PREFER_CONFIG 的 config 查找命中
   （实测 CMakeCache 出现 `ZLIB_DIR=~/.harmonybrew/lib/cmake/ZLIB`，链接命令带上
   zlib-ng 绝对路径、NEEDED 写成 libz.so.1）。需同时把该前缀排除出查找面：

   ```python
   if self.settings.os == "OHOS":
       _brew = os.path.join(os.path.expanduser("~"), ".harmonybrew")
       if os.path.isdir(_brew):
           tc.cache_variables["CMAKE_IGNORE_PREFIX_PATH"] = _brew
   ```

2. 用 `tc.cache_variables`（**cache 变量**）预设各 Find 模块的 cache 变量
   （模块执行时 find_path/find_library 见 cache 已有值即直接命中，不再搜索）：

   ```python
   tc.cache_variables["ZLIB_ROOT"]         = z.package_folder
   tc.cache_variables["ZLIB_INCLUDE_DIR"]  = os.path.join(z.package_folder, "include")
   tc.cache_variables["ZLIB_LIBRARY"]      = os.path.join(z.package_folder, "lib", "libz.a")
   tc.cache_variables["HDF5_ROOT"]         = hdf5.package_folder
   tc.cache_variables["NETCDF_INCLUDE_DIR"] = os.path.join(nc.package_folder, "include")
   tc.cache_variables["NETCDF_LIBRARY"]     = os.path.join(nc.package_folder, "lib", "libnetcdf.so")
   ```

   要点：
   - **必须 `tc.cache_variables` 而不是 `tc.variables`**：`tc.variables` 写出
     普通变量 `set(...)`，Find 模块里的 find_path/find_library 只认 **cache**——
     普通变量预设被无视，find_library 照样重新搜索（本包首版即因此链到
     harmonybrew zlib-ng）。
   - **HDF5 不预设 `HDF5_LIBRARY`**：FindHDF5 的库变量名带组件与语言后缀
     （`HDF5_C_LIBRARY`/`HDF5_${lang}_LIBRARY_${lib}`，随 CMake 版本漂移）；
     它的全部 `find_path/find_library` 都带 `HINTS ${HDF5_ROOT}`（设备
     cmake-4.1 `Modules/FindHDF5.cmake:666-1118` 实读），预设 `HDF5_ROOT`
     一处即可整体命中。
   - **上游自带的 FindNETCDF.cmake 无任何 root 语义**（只搜 /usr/include 等
     硬编码路径），必须直接预设结果变量 `NETCDF_INCLUDE_DIR/NETCDF_LIBRARY`。
   - zlib 动静态跟随依赖图既有形态：本仓 ohpcd 的 hdf5/netcdf 都静态链
     `libz.a`（`readelf -d` 无 libz NEEDED，实测），`ZLIB_LIBRARY` 指向
     `libz.a` 保持一致（clucene-core 先例同型）。
   - `find_package(X)` 的模块 cache 变量名是稳定 API（`ZLIB_LIBRARY`、
     `ZLIB_INCLUDE_DIR`、`NETCDF_INCLUDE_DIR/NETCDF_LIBRARY`、`<pkg>_ROOT`），
     与 CMakeDeps 的小写 config 变量不同名——预设错名字等于没设。

3. 兜底：把全部依赖 `cpp_info.includedirs/libdirs` 以 `-I/-L` 注入
   `CMAKE_<LANG>_FLAGS` 与 `*_LINKER_FLAGS`（libmatio 的
   --inject-dep-includes/--inject-dep-libdirs 生成模式），任何模块分支漏接时
   编译/链接仍能命中 conan 包内路径。

## 判别要点（出现下列形态即按本条排查）

- `CMakeCache.txt` 出现 `ZLIB_DIR`/`<Dep>_DIR` 指向非 conan 路径（harmonybrew、
  /usr 等）——config 模式被第三方包抢跑的直接证据。
- 链接命令（`CMakeFiles/<t>.dir/link.txt`）里出现非 conan 的库绝对路径。
- `CMakeError.log`/configure 日志里 `Found HDF5:` 一行都出现，但 `HDF5_INCLUDE_DIRS`
  为空（或 target 缺失报 `Target "ZLIB::ZLIB" not found`）。
- 静态库（`libz.a`）出现在上游 CMake 的变量消费路径而共享库期望失效——先
  `readelf -d <依赖>.so | grep NEEDED` 确认依赖图真实形态再选 `.a/.so`。
- 配方里 `find_package` 相关的「编译期才炸、configure 不炸」级联错误。
- **NEEDED 指向 CI 不受控路径**（libz.so.1 等）：`readelf -d <产物>.so | grep NEEDED`
  逐项核对解析来源，凡不在 conan 闭包/系统 libc 内的都要归因。

## 本次验证

libminc 2.5.0 新包适配（archives/l/libminc/2.5.0）：设备（OHOS aarch64）真机
`conan create` 通过；上游 ctest 套件（testdir/ 注册用例）与 test_package
（MINC2+MINC1 双链路消费者，`H5Fis_hdf5`/`ncinq` 底层指纹断言）真跑通过。
复现命令见 `$HOME/tmp/libminc-2.5.0/reproduce-e632.sh`（任务私有目录）。

## 适用范围与安全边界

适用于「上游 CMake 按模块模式变量/target 消费 conan 依赖」的全部包（CMake
项目读 `${HDF5_*}`/`${ZLIB_*}`/`${NETCDF_*}` 或链 `ZLIB::ZLIB` 即命中）。
不适用于已按 config target 消费（`find_package(hdf5 CONFIG)` / `hdf5::hdf5`）
的包——那类直接用 CMakeDeps 即可，预设反而多余。`cmake_find_mode=none` 后
CMakeDeps 不再为该依赖生成 config，其他仍走 config 的消费方（若有）需自行
补齐；预设的 cache 变量只影响 find_package 语义，不改变编译器默认搜索路径。
