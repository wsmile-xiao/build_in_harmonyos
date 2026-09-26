# CMake 带 VERSION/SOVERSION 的共享库在 HarmonyOS HMDFS 上创建符号链接失败，需去版本号产扁平 .so

- **草稿 ID**: DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink
- **来源**: libfreenect 0.5.3 HarmonyOS PC 适配（HMDFS 符号链接失败 + 上游自定义 Find 模块绕过）
- **分类**: cmake / conan / posix-library / shared-lib / filesystem
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **构建阶段链接共享库时报错**：
  ```
  CMake Error: failed to create symbolic link '../lib/libfreenect.so.0.5': Permission denied
  CMake Error: cmake_symlink_library: System Error: Permission denied
  make[2]: *** [src/CMakeFiles/freenect.dir/build.make:215: lib/libfreenect.so.0.5.3] Error 1
  ```
- **复现命令**：`conan create` 在 OHOS aarch64 目标上构建带 `set_target_properties(... VERSION ... SOVERSION ...)` 的 CMake SHARED 库。

## 根因

1. **CMake 版本化软链**：当 CMake 给 SHARED 目标设置 `VERSION`/`SOVERSION` 时，构建系统会在 `lib/` 下生成
   `lib<name>.so.<major>.<minor>`（真文件）并创建符号链接 `lib<name>.so.<major> -> lib<name>.so.<major>.<minor>`、
   `lib<name>.so -> lib<name>.so.<major>`。
2. **HMDFS 不支持符号链接**：HarmonyOS 真机的 `/storage` 是 HMDFS，不支持 `symlink(2)`，
   `cmake_symlink_library` 创建软链时返回 `Permission denied`，导致链接步骤直接失败（编译已通过）。
3. 与"找不到库/头文件"类错误不同：本错误发生在**链接产物落地**阶段，源码与编译均正常。

## 最小修复方案

在 `archives/<letter>/<package>/<version>/**` 范围内，**去掉版本号让 CMake 只产扁平 .so**：

1. **配方** `conanfile.py` 的 `source()` 中用 `replace_in_file` 移除 `VERSION`/`SOVERSION`：
   ```python
   from conan.tools.files import replace_in_file

   def source(self):
       get(self, **self.conan_data["sources"], strip_root=True)
       # HMDFS 不支持符号链接；去版本号，避免 CMake 建 libx.so.0.5.3 -> .so.0.5 -> .so 软链
       cmf = os.path.join(self.source_folder, "src", "CMakeLists.txt")
       replace_in_file(self, cmf,
           "set_target_properties ( freenect PROPERTIES\n  VERSION ${PROJECT_VER}\n  SOVERSION ${PROJECT_APIVER})",
           "# versioning dropped: HMDFS has no symlinks (flat .so)")
   ```
   - 若有第二个共享库（如 `libfreenect_sync`），对其 `CMakeLists.txt` 做同样处理。
   - 不要用 `#ifdef __OHOS__` 之类宏去改上游源码；在配方 `source()` 阶段统一替换即可。

2. **package_info()** 仍按库名声明：
   ```python
   self.cpp_info.libs = ["freenect", "freenect_sync"]
   ```
   扁平 `libfreenect.so` 即可被消费者链接，无需 DT_SONAME 软链。

## 同时发现并解决的相关点：上游自定义 Find 模块绕过

上游 `cmake_modules/Findlibusb-1.0.cmake` 用 `find_path`/`find_library` 写死 `/usr/include`、`/usr/lib`，
且文件顶部 `if(LIBUSB_1_LIBRARIES AND LIBUSB_1_INCLUDE_DIRS)` 命中**复数** cache 变量即短路返回。
在 `generate()` 直接把 conan 依赖包的路径写进复数 cache 变量即可绕过硬编码：

```python
libusb = self.dependencies["libusb"]
usb_inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0], "libusb-1.0.so")
tc.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = usb_inc
tc.cache_variables["LIBUSB_1_LIBRARIES"] = usb_lib
```

## 实际验证结果

- **真机**：HarmonyOS HongMeng Kernel 1.12.0 aarch64（clang 15.0.4），profile `ohos-aarch64-fixed`。
- **构建**：`conan create . --profile:h=ohos-aarch64-fixed -c tools.build:jobs=1` 通过。
  - 产物：`libfreenect.so/.a`、`libfreenect_sync.so/.a`、`pkgconfig/`、`include/libfreenect/*.h`。
- **消费者用例（2 个，均实跑通过）**：
  1. `test_freenect.c`：调用 `freenect_init() -> freenect_num_devices() -> freenect_shutdown()`。
  2. `test_sync.c`：链接 `libfreenect_sync` 头文件并调用 `freenect_sync_stop()`（无设备时安全空操作）。
  - OHOS 沙箱无物理 Kinect 时 `freenect_init()` 返回 -99，测试优雅容忍，验证"可链接可调"这一硬目标。

## 适用范围

- 在 HarmonyOS PC（HMDFS）上用 CMake 构建、且 SHARED 目标设置了 `VERSION`/`SOVERSION` 的 POSIX C/C++ 库。
- 任何 `cmake_symlink_library: ... Permission denied` / `failed to create symbolic link *.so*` 报错。

## 非适用边界

- 产物只需要静态库（无 .so）的包不会触发该软链问题。
- 目标文件系统为常规 ext4/tmpfs（支持 symlink）的构建环境无需此处理。
- 不要把"去版本号"误用于依赖 DT_SONAME 版本解析的动态加载场景；本仓库 POSIX 三方库用扁平 .so 即可。

## 查重差异

- 与 E092（CMake 平台识别）相关但不同：本条目针对**链接产物阶段的 HMDFS 符号链接限制**，
  给出"去 VERSION/SOVERSION 产扁平 .so"的可复用配方改法，以及如何识别该类错误签名。
- 补充了"上游自定义 Find*.cmake 用复数 cache 变量短路"这一绕过模式，供后续 USB/硬件类库参考。

## 关联原则

- P010：尊重上游构建逻辑，用 Conan 配方在 `source()` 阶段做最小替换，而非改上游测试。
- P020：消费者测试必须真实调用 API（init/stop），验证可链接可调，而非空壳。

## 禁止模式

1. **保留 VERSION/SOVERSION 指望软链成功**：HMDFS 必然 `Permission denied`，链接阶段失败。
2. **用 `#ifdef __OHOS__` 宏改上游源码**：不符合本仓库"配方侧最小替换"约定，且污染上游源码树。
3. **直接 `self.run("test")` 空壳**：消费者测试必须真实调用被测 API。

## 关联交付

- 本草稿与 `archives/l/libfreenect/0.5.3/**` 同属一次交付。
- 正式 E 编号由知识库主编审核后分配。
