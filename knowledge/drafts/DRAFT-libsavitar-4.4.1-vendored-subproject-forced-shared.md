# DRAFT-libsavitar-4.4.1-vendored-subproject-forced-shared — CMake 内嵌子工程被 Conan shared 强制共享化导致 NEEDED 相对路径断链

> 草稿知识项 — CMake add_subdirectory 内嵌 vendored 子工程在 Conan
> shared=True 配方下被 toolchain 强制 BUILD_SHARED_LIBS=ON 建成共享库，
> 父共享库 NEEDED 记录 "子目录/子库.so" 相对路径且子库不随父库 install
> 规则安装 → 运行时断链；修复为子工程作用域补丁强制静态内嵌。
> 来源：libsavitar 4.4.1 适配（task libsavitar-4.4.1-r01-pc2-37，
> 2026-09-27）
> 同 stem 配对：`knowledge/drafts/DRAFT-libsavitar-4.4.1-vendored-subproject-forced-shared.kv`

## 问题（现象 / error_signature）

`conan create` 后 test_package 运行报：

```
Error loading shared library pugixml/libpugixml.so: (needed by ./test_libsavitar)
Error relocating ./test_libsavitar: _ZN7Savitar13ThreeMFParserC1Ev: symbol not found
ERROR: libsavitar/4.4.1@ohpcd/stable (test package): Error in test() method
```

父库 `readelf -d libSavitar.so` 显示：

```
NEEDED  pugixml/libpugixml.so   ← 带子目录的相对路径，非标准 SONAME
```

## 根因（root_cause）

1. 父库配方 `default_options = {"shared": True}` 时，Conan CMakeToolchain
   在 conan_toolchain.cmake 中强制 `BUILD_SHARED_LIBS=ON`（日志可见
   "Conan toolchain: Setting BUILD_SHARED_LIBS = ON"）。
2. 上游 `add_subdirectory(pugixml)` 内嵌的子工程（pugixml/CMakeLists.txt
   的 `option(BUILD_SHARED_LIBS ... OFF)` 默认静态）被子工程的
   `if(BUILD_SHARED_LIBS)` 分支生效 → 子工程也建成共享库。
3. 父共享库链接子共享库时，OHOS 上链接器把 NEEDED 记录成
   "pugixml/libpugixml.so" 这种**带子目录的相对路径**（E207 同源现象）。
4. 父库 `install(TARGETS Savitar EXPORT ...)` 只安装父目标，子工程的
   libpugixml.so 不会被带出；test_package 加载父库时按该相对路径找
   不到 → 断链。手工复制实体文件也无法命中（NEEDED 前缀带子目录）。

> 额外陷阱：在配方 generate() 里 `tc.variables["BUILD_SHARED_LIBS"]="OFF"`
> 无效——Conan 按 shared 选项重新覆盖该变量，需在**子工程 CMakeLists
> 作用域**内用普通变量强制。

## 方案（solution）

补丁强制子工程静态（普通变量遮蔽 cache 值，只影响子目录作用域）：

```diff
--- a/pugixml/CMakeLists.txt
+++ b/pugixml/CMakeLists.txt
@@ -1,5 +1,6 @@
 project(pugixml)
 cmake_minimum_required(VERSION 2.6)
+set(BUILD_SHARED_LIBS OFF)
 option(BUILD_SHARED_LIBS "Build shared instead of static library" OFF)
```

父共享库链接静态子库时符号内嵌进父 .so → NEEDED 不再记录子库路径，
运行时无需子库实体。conandata.yml 登记补丁（patch_type: portability）。

## 验证（verification）

1. `readelf -d 父库.so`：NEEDED 不再含 `pugixml/libpugixml.so`；
2. 包内 lib/ 无子库 .so（仅静态 .a 或不打包）；
3. test_package 消费者二进制正常运行。

本库实测：补丁后 `conan create` G2 PASS，test_package 输出
"parse OK / serialize OK"，W3 本地 CI L0/L1/L5 全 pass。

## 适用边界（applicability）

父库为共享库 + add_subdirectory 内嵌 vendored 子工程 + 配方
shared=True 的 CMake 库，在 OHOS/HarmonyOS PC Conan 2 下适配时适用。
父库静态、或子工程本就被父库 install 带出安装时不适用。

## 反例与限制（counterexample / limitations）

若子工程是独立交付的共享库（父库 install(EXPORT) 带出并安装），不应
强制静态。强制静态会改变包内布局（无子库独立 .so），下游若需独立链接
子库 ABI 则不适合。