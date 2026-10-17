# E615 — CMake+Conan 适配的四类确定性陷阱（宿主依赖静默回退 / 生成器吞掉 `$LD_LIBRARY_PATH` / 传递依赖头文件不传播 / 上游安装清单漏头文件）

来源任务：`feat/libcomps-0.1.24`（libcomps 0.1.24，CMake + C 库 + Python 3 绑定，全新包）。
以下四条都在同一台 OHOS 设备上**实测复现并验证修法**。

## 错误签名

```
ld.lld: error: unable to find library -lexpat
Error relocating ./test_comps: XML_ParserCreate: symbol not found
Error loading shared library libxml2.so.16: No such file or directory
fatal error: 'libxml/encoding.h' file not found
fatal error: 'comps_types.h' file not found
check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
```

## 陷阱 1：宿主依赖静默回退（最危险，无任何报错字样）

Conan 的 `CMakeToolchain` 会写 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`。
若配方**没有调用 `CMakeDeps(self).generate()`**，且上游读的是 CMake Find 模块的
**旧式大写变量**（`LIBXML2_LIBRARY` / `LIBXML2_LIBRARIES` / `EXPAT_LIBRARY` /
`ZLIB_LIBRARIES` / `ZLIB_INCLUDE_DIRS`），那么 `find_package` / `find_library` 会命中
设备 PATH 上 `~/.harmonybrew` 的 `*-config.cmake`：

```
CMakeCache.txt:
  LIBXML2_LIBRARY:FILEPATH=/storage/.../.harmonybrew/Cellar/libxml2/2.15.4_1/lib/libxml2.so
  ZLIB_DIR:PATH=/storage/.../.harmonybrew/lib/cmake/ZLIB
link 行:
  /storage/.../.harmonybrew/lib/libz.so.1.3.1.zlib-ng
```

**后果**：设备上全绿，干净 worker 上必红（设备事实 §一.4 的经典形态），
而日志里没有任何可疑字样。

**修法**：调用 `CMakeDeps` + 把上游读到的每个变量钉到 Conan 包目录，然后
**用链接行与 CMakeCache 验证**（`grep -c harmonybrew` 必须为 0），不要只看退出码。

## 陷阱 2：构建生成器吞掉 `$LD_LIBRARY_PATH`（换 Ninja 无效）

上游把 shell 片段直接内联进 `add_custom_target` 的 `COMMAND`：

```cmake
COMMAND export LD_LIBRARY_PATH="${LIBCOMPS_OUT}/:$LD_LIBRARY_PATH" && ./test_comps
```

CMake 把这行原样写进生成器文件，于是：

* **Makefile 生成器**：`$L` 被当成 make 变量引用 → 展开为空；
* **Ninja 生成器**：`$LD_LIBRARY_PATH` 被当成 ninja 变量引用 → 展开为空。

两种生成器都把命令退化成 `export LD_LIBRARY_PATH="<build>/src/:"`，
继承来的依赖库搜索路径被清空，测试二进制随即 `Error relocating ...: symbol not found`。
**实测：把生成器从 Unix Makefiles 换成 Ninja 并不解决问题**（同一根因）。

**修法**：补丁把 `$LD_LIBRARY_PATH` 写成 `$$LD_LIBRARY_PATH`——两种生成器都会把 `$$`
还原成单个 `$` 交给 shell，继承值得以保留。

## 陷阱 3：传递依赖的头文件默认不传播

Conan 2 的 `transitive_headers` 默认为 `None`（等于不传播）。
若被测库的**公开头文件**包含依赖的头（libcomps 的 `comps_utils.h` 含
`<libxml/encoding.h>`、`comps_parse.h` 含 `<expat.h>`），消费者拿到的 CMakeDeps config 里
传递依赖的 `*_INCLUDE_DIRS_RELEASE` 是**空的**：

```
# test_package/generators/libxml2-release-armv8-data.cmake（传递图）
set(libxml2_INCLUDE_DIRS_RELEASE )
# 同一依赖在“直接 requires”图里
set(libxml2_INCLUDE_DIRS_RELEASE "${libxml2_PACKAGE_FOLDER_RELEASE}/include/libxml2" ...)
```

**修法**：`self.requires("libxml2/2.15.3.1", transitive_headers=True)`，expat 同理。
不要改用 `cpp_info.requires` 绕——一旦声明它，Conan 会要求**每个**直接依赖都被引用
（`python`、`zlib` 也得列进去），副作用更大。

## 陷阱 4：上游安装清单漏头文件

`install(FILES ${libcomps_HEADERS} DESTINATION include/libcomps)` 是显式清单，而清单内的
`comps_log.h` 会 `#include "comps_types.h"`。对安装集合做包含闭包：

```
清单（去掉被注释的 `#comps_list.h`）25 个头、包含闭包 26 个 → 差集 = ['comps_types.h']（补丁后安装 26 个）
```

上游 RPM 用 `%{_includedir}/libcomps/*.h` 通配安装，掩盖了该缺陷；按 CMake 显式清单打包
必然暴露，且**任何消费者都无法编译**。修法：补丁把缺的头加进 `*_HEADERS`。

## 附带判据：check 套件在 /tmp 只读设备上

`check 0.15.2` 的 IPC 临时文件受 `TEMP` / `TMPDIR` 控制（不是硬编码 `/tmp`）：

```sh
TMPDIR=<可写目录> TMP=$TMPDIR TEMP=$TMPDIR CK_FORK=no ./test_binary
```

只设 `CK_FORK=no` 不足以消除
`check_msg.c:317: Unable to create temporary file for communication`。

## 复现与验证命令

```sh
# 元凶定位（陷阱 2）
grep -n "LD_LIBRARY_PATH" <build>/build.ninja <build>/tests/CMakeFiles/*_run.dir/build.make

# 陷阱 1 的验证（期望 0）
grep -c harmonybrew <build>/CMakeCache.txt <build>/build.ninja

# 陷阱 3 的对照
diff <直接-requires-图>/libxml2-release-armv8-data.cmake <传递-图>/libxml2-release-armv8-data.cmake

# 陷阱 4 的闭包计算
python3 - <<'PY'
import io, os, re, glob
src = "<src>/libcomps/src"
cml = io.open(os.path.join(src, "CMakeLists.txt"), encoding="utf-8").read()
installed = [t for t in re.search(r"set \(libcomps_HEADERS(.*?)\)\s*\n", cml, re.S).group(1).split()
             if t.endswith(".h")]
inc = {os.path.basename(p): re.findall(r'#include\s+"([^"]+)"', io.open(p, encoding="utf-8").read())
       for p in glob.glob(os.path.join(src, "*.h"))}
seen, stack = set(), list(installed)
while stack:
    h = stack.pop()
    if h in seen:
        continue
    seen.add(h)
    stack += [n for n in inc.get(h, []) if n.endswith(".h") and n not in seen]
print("missing:", sorted(seen - set(installed)))
PY
```

## 关键要点

1. **依赖解析要看链接行，不要看退出码**——宿主回退在设备上完全静默。
2. **`$` 在 CMake `COMMAND` 里必须写成 `$$`**，否则被构建生成器吃掉；Make 与 Ninja 同病。
3. **公开头文件包含谁的依赖头，谁就要 `transitive_headers=True`**。
4. **显式安装清单要做包含闭包核对**；RPM 的通配安装会掩盖漏项。
