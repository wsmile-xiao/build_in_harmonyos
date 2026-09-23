# DRAFT — libtool 依赖的 `.la` 不能跨包复用，与"私有头文件依赖"的声明方式

> 状态：草稿，待评审提升为 E 条目。配套 `.kv` 文件同名同目录。
> 来源：`archives/l/libwpd/0.10.3/`（设备实机，2026-09-14）

## 坑 1：`libtool: library '...la' was moved`

### 现象

```
libtool: warning: library '.../librevenge-0.0.la' was moved.
libtool:   error: cannot find the library '//lib/librevenge-0.0.la' or unhandled argument '//lib/librevenge-0.0.la'
make[4]: *** [Makefile:443: wpd2raw] Error 1
```

### 根因

libtool 的 `.la` 文件里记录了**它自己的安装前缀**（`libdir`）。依赖包若以
`--prefix=/` + DESTDIR 打包（本仓 librevenge 0.0.5 正是如此），它的 `.la` 里
`libdir='//lib'`。

下游配方写 `-L<依赖包>/lib -lrevenge-0.0` 时，libtool 会先在 `-L` 目录里找同名
`.la`，并**按 .la 里记录的 libdir** 去解析库路径 —— 而 `//lib/...` 在本机不存在，
于是链接失败。这就是那条 "was moved" 警告的含义。

### 错误解法：直接给 `.a` 绝对路径

绕过 `.la` 的直觉做法是把库写成绝对路径：

```
REVENGE_LIBS = /.../p/lib/librevenge-0.0.a -L.../zlib/lib -lz
```

这确实绕过了 `.la`，但 libtool 会把命令行上的 `.a` 当成**输入成员**归档进产物：

```
ld.lld: warning: ../../lib/.libs/libwpd-0.10.a: archive member
                 'librevenge-0.0.a' is neither ET_REL nor LLVM bitcode
```

依赖库被**嵌进**了 `libwpd-0.10.a`。消费者如果再链一次 librevenge（很常见：libwpd
的公共头就要用 `librevenge::RVNGInputStream`），就会撞上重复符号。

### 正确解法：只放 `.a` 的"干净 `-L` 目录"

在构建目录里建一个目录，只把依赖的 `.a` 复制进去（**不要** `.la`）：

```python
clean = Path(self.build_folder, ".revenge-libs")
clean.mkdir(parents=True, exist_ok=True)
for name in ("revenge-0.0", "revenge-generators-0.0", "revenge-stream-0.0"):
    source = Path(self._revenge_archive(name))   # 优先 .a，回退 .so
    copy(self, source.name, src=str(source.parent), dst=str(clean), keep_path=False)
```

然后正常写 `-L<干净目录> -lrevenge-0.0`。libtool 找不到 `.la`，就走普通的
`-L/-l` 路径：既不误读 libdir，也不把依赖当成员归档。

## 坑 2：私有头文件依赖必须用 `tool_requires`

libwpd 的 `src/lib/libwpd_internal.cpp` 包含 `<boost/spirit/include/qi.hpp>`，
它的 `configure.ac` 也硬检查该头：

```m4
CPPFLAGS="${BOOST_CFLAGS} ${CPPFLAGS}"
AC_CHECK_HEADERS([boost/spirit/include/qi.hpp], [],
                 [AC_MSG_ERROR([Required boost headers not found.])])
```

但 boost **不出现在 libwpd 的公共头与链接接口里**（`inc/libwpd/*.h` 无 boost 包含，
spirit 是 header-only）。所以：

- 写成 `self.requires("boost/...")` → conan 的 `package_info()` 直接拒绝：

  ```
  ERROR: package_info(): The direct dependency 'boost' is not used by any
         '(cpp_info/components).requires'.
  ```

- 而把它塞进 `cpp_info.requires` 又等于向消费者谎报一个并不需要的依赖。

正确做法是声明为构建期依赖：

```python
def requirements(self):
    self.requires("librevenge/0.0.5")   # 公共头与链接接口都需要 → requires
    ...
def build_requirements(self):
    self.tool_requires("boost/1.90.0.3")  # 只被自己的 TU 用 → 构建期
```

并相应地从 `self.dependencies.build["boost"]` 取包目录；版本与图中已有版本
（librevenge 依赖的 boost）对齐，避免出现两份 boost。

## 附：无 pkg-config 时把 `PKG_CHECK_MODULES` 逐个喂饱

该宏在对应的 `<PREFIX>_CFLAGS` 非空时**短路**，根本不调用 pkg-config，所以每个检查
都要给一组变量：

```sh
REVENGE_CFLAGS / REVENGE_LIBS
REVENGE_GENERATORS_CFLAGS / REVENGE_GENERATORS_LIBS
REVENGE_STREAM_CFLAGS / REVENGE_STREAM_LIBS
```

静态依赖自身的传递库也要带上（librevenge 的 stream 层需要 `-lz`），否则
`*_LIBS` 看似齐全，链接期仍报 undefined symbol。

## 验证（libwpd 0.10.3，设备实机）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: libwpd 0.10.3
```

- 库级消费者测试 9/9：格式识别正负例（正例用手工构造的合法 WPX 头拿到
  `WPD_CONFIDENCE_EXCELLENT`）、非 WordPerfect 输入下 parse 与 verifyPassword 的失败契约
- CLI 级 5/5：对安装后的 `wpd2text` 验证缺失文件/纯文本被干净拒绝、畸形输入不崩溃

## 适用边界

- 适用于"依赖包由 libtool 构建、且本包也是 libtool 工程"的 autotools 配方。
  **librevenge / libwpd / libwps / libabw 这一族完全同构**，libabw 会原样遇到全部三个坑。
- 依赖包若是 cmake/meson 构建（不产 `.la`），坑 1 无关；坑 2、附注仍然适用。
- 若依赖的头确实出现在公共头里（如 librevenge 之于 libwpd：消费者要自己实现
  `RVNGInputStream`），那它就**必须**是 `requires` 而非 `tool_requires`。
