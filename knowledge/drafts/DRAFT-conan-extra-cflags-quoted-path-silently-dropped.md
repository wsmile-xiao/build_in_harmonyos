# DRAFT-conan-extra-cflags-quoted-path-silently-dropped — `-I"path"` 被 CMake 静默丢弃

## 现象

`conan create` 在编译阶段报头文件找不到，但**路径本身是对的**：

```
unix/libusb/libfli-usb-sys.c:46:10: fatal error: 'libusb-1.0/libusb.h' file not found
#include <libusb-1.0/libusb.h>
```

关键在于：Conan 的 libusb 包里 `include/libusb-1.0/libusb.h` 确实存在，
`-I` 也确实指对了目录，flag 却没生效。

## 根因

配方里写的是 shell 习惯的引号包裹：

```python
tc.extra_cflags.append(f'-I"{usb_inc}"')
```

Conan 的 `CMakeToolchain` 把 `extra_cflags` **原样嵌进 CMake 源码字符串**，
生成：

```cmake
string(APPEND CONAN_C_FLAGS " -I"/root/.conan2/p/libus04e54d4f229a5/p/include/libusb-1.0"")
```

这行是非法 CMake 语法（`""` 之间的 `"` 提前终止字符串）。CMake 只报一条
dev warning 就继续解析，`-I` 整段**没有进入 `CMAKE_C_FLAGS`**：

```
CMake Warning (dev) at .../conan_toolchain.cmake:68:
  Syntax Warning in cmake code at column 34
  Argument not separated from preceding token by whitespace.
```

双重静默：路径写错没告警；路径加了引号，flag 被丢弃也只有一条 dev warning。

## 排查路径（三条岔路，第二条是陷阱）

```bash
# 决定性证据：看 Conan 到底生成了什么
$ grep -n 'CONAN_C_FLAGS' <build>/generators/conan_toolchain.cmake | head
68:string(APPEND CONAN_C_FLAGS " -I"/root/.conan2/p/libus04e54d4f229a5/p/include/libusb-1.0"")
#                                     ↑ 内层引号截断字符串

# 岔路 1（错）：怀疑 Conan 包布局不对
$ ls /root/.conan2/p/libus*/p/include/libusb-1.0/libusb.h
/root/.conan2/p/libus04e54d4f229a5/p/include/libusb-1.0/libusb.h     # 存在
# → 包没问题，别去动包

# 岔路 2（错得更远）：改用 CMAKE_INCLUDE_PATH 赋值
#   tc.variables["CMAKE_INCLUDE_PATH"] = usb_inc
$ conan create ...
CMake Error at cmake_modules/FindINDI.cmake:285 (message):
  Could not find INDI include directory
# → 报错漂移到了 INDI！因为赋值覆盖了 toolchain 生成的
#   list(PREPEND CMAKE_INCLUDE_PATH ...) 列表，把 libindi 的 include 挤掉了
$ grep -n 'CMAKE_INCLUDE_PATH' <build>/generators/conan_toolchain.cmake
148:list(PREPEND CMAKE_INCLUDE_PATH ".../libindi/include" ... ".../libusb.../include/libusb-1.0" ...)

# 岔路 3（对）：确认要注入的是「根目录」而不是子目录
#   toolchain 只把叶子目录 .../include/libusb-1.0 加进 CMAKE_INCLUDE_PATH，
#   而源码写的是 <libusb-1.0/libusb.h>，需要的是包含 libusb-1.0/ 的那一层
```

## 修复

```python
usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
if os.path.basename(usb_inc) == "libusb-1.0":
    usb_inc = os.path.dirname(usb_inc)
tc.extra_cflags.append(f"-I{usb_inc}")          # ← 无内层引号
```

Conan 生成的 CMake 代码本身提供字符串边界，缓存路径不含空格时不需要 shell 式引号。

## 验证

```
$ conan create . -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# 无 Syntax Warning，14 个源文件全部编译通过
[ 92%] Building C object CMakeFiles/fli.dir/unix/linux/libfli-parport.c.o
[ 92%] Building C object CMakeFiles/fli.dir/unix/libusb/libfli-usb-sys.c.o
[100%] Linking C shared library libfli.so
```

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `E092`（CMake 不识别 HarmonyOS） | 都是 cmake/Conan 工具链层问题 | E092 是**平台识别**；本条是 **Conan 生成层 → CMake 解析层**的引号截断，平台设对了照样命中，且报错指向"头文件缺失"极具误导性 |
| `DRAFT-ohos-fortify-source-defeats-libc-wrap-mock` | 都是"静默失效"类 | 那条是 fortify 改写调用点符号导致 `--wrap` 失配；本条是 flag 字符串在 CMake 里被截断。机制与症状都不同 |
| `E999-draft-8FBE`（libc 符号族 configure 误检） | 都会被误判成"包没装好" | E999 在 autoconf 探测层；本条在编译期 include 路径，且与 libc 符号无关 |

## 禁止做法

| 禁止 | 原因 |
|---|---|
| `tc.variables["CMAKE_INCLUDE_PATH"] = <path>` | 赋值覆盖 toolchain 的 `list(PREPEND ...)`，把其它依赖 include 顶掉，报错漂移到无关依赖 |
| 用 `echo ... >> CMAKE_C_FLAGS` 之类把 flag 拼进命令行字符串 | 绕过 Conan toolchain，本机绿 CI 红 |

## 来源

- 上游任务：archives/l/libfli/2.0-20221221182632
- 复现命令：`conan create . -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing`
- 关键证据文件：`<build>/generators/conan_toolchain.cmake` 第 68 行
