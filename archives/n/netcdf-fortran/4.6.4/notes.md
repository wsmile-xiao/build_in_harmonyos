# netcdf-fortran 4.6.4 编译笔记（HarmonyOS PC · Conan cmake · Fortran）

## 定位

netCDF 的 Fortran 接口库（`libnetcdff.so`），给 F77 / F90 / F2003 程序提供
`use netcdf` 之上的 API。上游是 Fortran 2003 源码，链接 netcdf-c。

- 包依赖：`netcdf/4.9.3`（netcdf-c，带 HDF5/SZIP/QUANTIZE/ZSTD/DAP）
- 工具依赖：`flang-ohos/20.1.0`（LLVM Flang 20.1.0）
- 产出：`lib/libnetcdff.so.7.1.0`（SONAME `libnetcdff.so.7`）、11 个 `.mod`、
  `include/netcdf.inc`、`bin/nf-config`、`lib/pkgconfig/netcdf-fortran.pc`、
  `lib/cmake/netCDF-Fortran/`

**本版本无需任何源码补丁**：51 项上游 CTest 在 OHOS 上原样全部通过，适配全部在配方侧。

## 关键适配

### 1. Fortran 工具链：设备/NDK 无 Fortran 编译器 → flang-ohos

设备与 OHOS NDK 都不带 `gfortran`/`flang`（`command -v flang gfortran` 均为空），
按仓库先例（openblas/lapack/libxc）用 `flang-ohos/20.1.0` 作 `tool_requires`。

`.mod` 是编译器私有的二进制接口，消费方必须用同一编译器，故
`self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")`。

### 2. ★ flang 必须当**链接驱动**，且链接 flag 要齐

flang-ohos 是精简运行集（无 `libclang_rt.builtins.a`、无 crt），所以 flang **不能**在没有
SDK 配合的情况下自己完成链接，会报：

```
ld.lld: error: cannot open Scrt1.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: unable to find library -lm / -lc / -l:libunwind.a
```

补齐三组参数后 flang 可以正常完成编译**和**链接（实测可执行文件与共享库都能出）：

| 参数 | 作用 |
|---|---|
| `--sysroot=<sdk>/sysroot` | 提供 `Scrt1.o`/`crti.o`/`crtn.o` 与 `libc`/`libm` |
| `-resource-dir=<sdk>/llvm/lib/clang/15.0.4` | 提供 `crtbeginS.o`/`crtendS.o` 与内建库 |
| `-L<sdk>/llvm/lib/aarch64-linux-ohos` | **提供 `libunwind.a`**，缺了必报 `unable to find library -l:libunwind.a` |

`-resource-dir` 由 `<sdk>/llvm/bin/clang -print-resource-dir` 现场问得，不写死版本号。

**为什么不能用 clang 顶替 Fortran 的链接规则**：曾试过在 toolchain 里覆盖
`CMAKE_Fortran_CREATE_SHARED_LIBRARY`/`CMAKE_Fortran_LINK_EXECUTABLE` 改成 `<CMAKE_C_COMPILER>`，
构建期 51 项 ctest 全过，但**安装后的包消费者加载失败**：

```
Error loading shared library libnetcdff.so.7: (needed by ./test_netcdf_fortran)
Error relocating ./test_netcdf_fortran: _FortranATrim: symbol not found
```

即 clang 链接出的 libnetcdff 无法为消费者提供 Fortran 运行时符号。改用 flang 驱动后正常。
（顺带发现：`<FLAGS>` 变量在 `CMAKE_Fortran_CREATE_SHARED_LIBRARY` 里不会展开，会被原样当
文件名传给编译器，报 `no such file or directory: 'FLAGS'`。）

- `-L<sdk>/llvm/lib/aarch64-linux-ohos` 放 `CMAKE_EXE_LINKER_FLAGS`/`CMAKE_SHARED_LINKER_FLAGS`
  而不是 `CMAKE_Fortran_FLAGS`：放编译 flags 会被 flang 每次编译都告警
  `argument unused during compilation`，实测 84 行噪音（改到链接 flags 后 0 行）。

### 3. ★ 安装期 RPATH 改写令 `.codesign` 失效 → 安装后必须重新签名

hnp 链接器会给产出的 `.so` 内置 `.codesign` 节。`cmake.install()` 会原位改写 RUNPATH
（字节改变、文件长度不变），宿主的签名随即失效，OHOS loader 拒绝加载该副本：

```
Error loading shared library libnetcdff.so.7: (needed by ./test_netcdf_fortran)
```

注意这行**没有 errno 文本**（不是"文件不存在"），且构建树里的同一份 `.so` 能正常加载。
实测证据（同一构建的两份拷贝）：

| 文件 | sha256 前 8 字节 | 消费者运行 |
|---|---|---|
| 构建树 `build-B/fortran/libnetcdff.so.7.1.0` | `f95d33b2…` | 通过 |
| 安装副本 `install/lib/libnetcdff.so.7.1.0` | `9d5b7fe9…` | RC 127，符号缺失 |

对安装副本重新签名后，同一消费者 **27/27 通过**。故配方把签名放在 `cmake.install()`
之后（先 `llvm-objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1`）。

### 4. 签名工具本身要干净的 `LD_LIBRARY_PATH`

`binary-sign-tool` 与 `llvm-objcopy` 是 C++ 程序，靠 loader 默认路径找 `libc++`。
构建期注入的 `LD_LIBRARY_PATH`（含各依赖 libdir）会遮蔽它，实测：

```
Error relocating /data/service/hnp/bin/binary-sign-tool: _ZNSt3__h4coutE: symbol not found
→ ConanException: Error 127 while executing
```

故调用这两个工具时显式 `env -u LD_LIBRARY_PATH`；同时 `build()` 结束前复原
`LD_LIBRARY_PATH`，不把构建期注入泄漏到 `package()` 阶段。

### 5. 上游 CMakeLists 的依赖发现方式（决定不能直接用 CMakeDeps）

- **netcdf-c**：上游走旧式变量接口（`netCDF_LIBRARIES`/`netCDF_INCLUDE_DIR`），并把它喂给
  `CHECK_LIBRARY_EXISTS()` —— 那里要的是**库文件路径**。给 imported target 名
  （`netcdf::netcdf`）会让全部特性探测静默失败，其中 `nc_def_var_szip` 探测失败直接
  `FATAL_ERROR`。故配方显式传 `libnetcdf.so` 的绝对路径。
- **hdf5**：上游在 netcdf-c 带 HDF5 时会 `FIND_PACKAGE(HDF5 COMPONENTS C HL REQUIRED)`。
  若让 CMakeDeps 生成 `hdf5-config.cmake`，配置模式先声明 `hdf5::hdf5` 再因缺组件回落模块模式，
  模块再去读 `hdf5::hdf5_hl` 就报
  `get_target_property() called with non-existent target "hdf5::hdf5_hl"`。
  故本配方**不生成 CMakeDeps**，改把 `HDF5_ROOT` 指向 hdf5 依赖包目录，让 CMake 自带的
  FindHDF5 模块按标准布局自行找到（实测三方案：`HDF5_ROOT` ✅；`CMAKE_PREFIX_PATH` ❌；
  逐个给 `HDF5_INCLUDE_DIR/HDF5_C_LIBRARY/HDF5_HL_LIBRARY` ❌）。

### 6. 其余

- `os=OHOS` 时把 `cmake_system_name` 显式设为 `OHOS`（conan 默认给 `HarmonyOS`，cmake 只有
  `Platform/OHOS.cmake`；名字不匹配时不报错，只让 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 等
  平台变量留空 → 产物丢 SONAME 并传染下游），带 os 守卫，同 netcdf-c 先例。
- 上游 `install(TARGETS ${t}_c DESTINATION lib)` 会把测试目标 `nf_test_c`/`ftest_c` 的
  OBJECT 库装进 `lib/objects-RelWithDebInfo/`，只因本配方开了 `ENABLE_TESTS` 才存在，
  `package()` 里删除。
- `bin/nf-config` 是配置脚本（非独立 CLI 工具），故不声明 `bindirs`、不建软件级
  `commands.json`（同 netcdf-c 先例）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| netcdf（netcdf-c） | 4.9.3 | 已发布，`conan install --build=never` 实测可取得 |
| flang-ohos | 20.1.0 | tool_requires，full_mode |

## 验证结果

上游 CTest（配方 `build()` 内真实执行，`build()` 里 `cmake.test()`）：

```bash
# 采信轮 conan create 的真实输出（配方 build() 内 cmake.test()）
$ grep -c '/51 Test ' reports/conan-create.log   # 51 行逐项结果 "N/51 Test #N ... Passed"
$ grep 'tests passed' reports/conan-create.log
100% tests passed, 0 tests failed out of 51
```

> 按仓库规则 R19（PR 中禁止 `*.log`），原始构建日志不入库；
> 逐字节抄录的证据行与日志 sha256 指纹见 `reports/verification-evidence.md`。

> 分母 51 的取数命令 `ctest -N`（输出 `Total Tests: 51`）在原生探索阶段执行；
> 上游默认 `ENABLE_TESTS=ON`，配方沿用默认并在 `build()` 内执行，两处分母一致。
> 随包日志里可直接复核的是 51 行 `N/51 Test #N ... Passed` 与上面那行汇总。
> （不要用 `grep -c 'Test  #'` 这种带对齐空格的写法：ctest 对 1–9 号用两个空格、
> 10 号以上只用一个，实测只会数到 9。）

51 项分布：`nf_test` 4 + `nf03_test` 2 + `nf_test4` 17 + `nf03_test4` 16 + `examples` 12。

`test_package` 两个消费者（均由 `conan create` 的 test_package 阶段真实执行）：

| 消费者 | 覆盖 | 结果 |
|---|---|---|
| `test_netcdf_fortran.f90`（Fortran 2003） | 建 netCDF-4 文件→定义维度/变量→写属性→开 HDF5 deflate→写数据→只读重开→格式/元数据/属性/数据逐项回读校验 | `27/27 passed` |
| `test_netcdf_fortran_abi.c`（C 侧契约） | 按 SONAME 以 `RTLD_NOW` 加载 `libnetcdff.so`（未解析符号即失败），再逐个 `dlsym` 解析 Fortran 消费者实际链接的 ABI 入口（`_QMnetcdfPnf90_*` 与 `_FortranA*`） | `10/10 passed` |

C 侧契约测试的存在理由：第 2 节记录的「clang 顶替 Fortran 链接规则」缺陷**只在消费者加载期暴露**，
而 Fortran 消费者报的也是运行期符号解析失败；该测试把这条交付面契约变成可自动执行的断言。
（它同时满足 CI 的 L0c 门禁——该门禁只识别 `.c/.cpp/.cc/.cxx/.sh/.py`，不认任何 Fortran 扩展名。）

## 注意事项

- 消费方（Fortran）需要用同一 `flang-ohos/20.1.0` 编译：`.mod` 是编译器私有格式。
- 消费方运行期需把 `libnetcdff.so` 与 netcdf-c 及其传递依赖（hdf5/curl/zstd/libxml2/libaec）
  放进 `LD_LIBRARY_PATH`——OHOS loader 不搜索包内绝对路径（`DT_RUNPATH` 被 `LD_LIBRARY_PATH` 覆盖）。
