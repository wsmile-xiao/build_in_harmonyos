# DRAFT-iowow-1.4.18-file-macro-rodata-path-leak

## 问题

`conan create` 全绿后，鸿蒙专项"无宿主路径"扫描在**Release 静态库**命中：

```console
$ strings -a libiowow-1.a | grep -E '/storage/|/home/|/Users/'
/storage/Users/currentUser/.conan2/p/b/iowow<hash>/b/src/utils/iwstw.c
```

构建无 `-g`（Release，`-O3 -DNDEBUG`），DWARF 调试段不存在，但绝对路径
仍嵌入 `.rodata.str1.1`。

## 根因

上游 IWLOG 日志宏用 `__FILE__`（如 iwstw.c 的线程池日志
`"iwstw | Thread iwstw_shutdown() from self thread: %lu"` 前拼接 `__FILE__`）。
CMake 编译源文件用**绝对路径**（`clang ... -c /abs/path/iwstw.c`），宏展开
把 conan 缓存路径固化进 rodata。

与 E579（minigraph，DWARF comp_dir）不同段位：

| | E579 | 本条 |
|---|------|------|
| 载体 | DWARF 调试段（-g） | .rodata（`__FILE__` 宏） |
| 构建 | Makefile 自带 -g | CMake Release 无 -g |
| 泄漏源 | cwd（source_folder）+ sysroot | 仅 source_folder（编译命令实参） |
| 映射需求 | 三重（source/build/toolchain） | 单映射 source 即归零 |

## 解决

配方 build() 给 CMake 注入 `-ffile-prefix-map`（单条 source 映射）：

```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    src = str(self.folders.base_source)
    cmake.configure(
        variables={"CMAKE_C_FLAGS": f"-ffile-prefix-map={src}=/iowow-src"}
    )
    cmake.build()
```

关键前提（已验证）：上游 `src/CMakeLists.txt` 是追加式
`set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ...")`，命令行 `-D` 注入的 flags
进入变量后**不被覆盖**、继续被追加。注入后 `strings` 命中归零，
conan create + test_package 30/30 全绿。

## 边界（适用条件与禁止）

- 适用：用 `__FILE__`/`__LINE__` 做日志/断言的 C/C++ 库 + CMake 构建
  （任何 Conan 缓存绝对路径场景）；Release/无 -g 交付产物同样需要扫描。
- 不适用/已覆盖：`-g` DWARF comp_dir 与 sysroot 路径泄漏用 E579 三重映射；
  Makefile 项目直接改 CFLAGS 即可（无注入点冲突问题）。
- 禁止：
  - 假设"无 -g 就无路径泄漏"——`__FILE__` 在 rodata，交付验收扫描照样命中；
  - 在不知道上游 CMakeLists 是否覆盖式 set(CMAKE_C_FLAGS ...) 前提下直接
    `-DCMAKE_C_FLAGS=...` 覆盖——若上游是覆盖式 `set(CMAKE_C_FLAGS "...")`
    会丢掉注入 flags（iowow 恰为安全的追加式，其他项目须先核查）。
- 备选：若上游 CMakeLists 是覆盖式，改用 `CMakeToolchain` 的
  `tc.variables["CMAKE_C_FLAGS"]` 追加或 environment 注入 CFLAGS。

## 验证

- 注入前：`strings -a libiowow-1.a | grep -c /storage/` = 1（T4 FAIL）；
- 注入后：归零（T4 PASS），conan create 全流程 + test_package 30/30 +
  鸿蒙专项 12/12 PASS；
- 上游追加式证据：`build/Release/src/CMakeFiles/iowow.dir/build.make` 中
  编译命令含注入的 prefix-map，且上游自身 flags（-std=gnu11 -Wall 等）
  全部保留。

## 相关

- similar_to: DRAFT-E579（同根因家族：构建路径嵌入产物；触发面变体：
  __FILE__/rodata/CMake vs DWARF/-g/Makefile）
