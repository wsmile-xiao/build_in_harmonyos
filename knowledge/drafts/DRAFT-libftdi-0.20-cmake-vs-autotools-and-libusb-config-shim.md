# libftdi 0.20 在 OHOS：上游自带两套构建系统时选 CMake（以及 autotools 路径的三个坑）

> 知识草稿（与 libftdi 0.20 归档适配 PR 一同交付）。
> 来源：libftdi 0.20 适配，`conan create`（ohos-aarch64 profile, clang 15）rc=0，
> 上游 `examples/find_all` 1/1（真机：`Number of FTDI devices found: 0`）、
> `test_package` 消费者断言 8/8 真机通过。
> 载体：libftdi 经 libusb 0.1 API 访问 FTDI 芯片；依赖 `libusb-compat/0.1.7`（底层 `libusb/1.0.27`）。

## 结论（先看这个）

当上游 tarball **同时提供 autotools 与 CMake** 时，OHOS 上优先选 CMake：

| 关注点 | autotools 路径 | CMake 路径 |
|--------|----------------|-----------|
| 找 libusb | `configure` 硬依赖 `libusb-config` 工具（制品包不提供）→ 需自写 shim | `FindUSB.cmake` 或直接用缓存变量 `LIBUSB_INCLUDE_DIR`/`LIBUSB_LIBRARIES` |
| 运行期探测 | native 模式会运行 conftest（动态依赖 `libusb-1.0.so.0`）→ 必须交叉模式 | 不做运行探测 |
| 链接 | 内置 libtool 2.2.6 在本环境写死 `ECHO="print -r --"` 且 `old_archive_cmds` 丢转义 | 不经过 libtool |
| 安装目录 | — | 需处理 `LIB_SUFFIX=64`、`UNIX` 未定义等上游假设（见下） |
| pkg-config 前缀 | `--prefix=/` + DESTDIR 失真，需重写 | CMakeToolchain 已把 `CMAKE_INSTALL_PREFIX` 指向包目录 |

下面的细节对"只有 autotools 的老工程"依然适用。

## 一、autotools 路径的三个坑（实测）

### 1. configure 硬依赖 `libusb-config`，制品包不提供

```m4
AC_CHECK_TOOL(HAVELIBUSB, libusb-config)
if test ! -z "$HAVELIBUSB"; then
   LIBUSB_CFLAGS=`$HAVELIBUSB --cflags`
   LIBUSB_LIBS=`$HAVELIBUSB --libs`
   ...
else
   AC_MSG_ERROR([*** libusb-config not found. You need a working libusb installation.])
fi
```

`libusb-compat/0.1.7` 包只有 `include/usb.h`、`lib/libusb.a`、`lib/pkgconfig/libusb.pc`，
**没有 `bin/libusb-config`**。最小 shim（只实现 configure 用到的三个选项）：

```sh
#!/bin/sh
prefix="<libusb-compat 包目录>"
case "$1" in
  --version) echo "libusb 0.1.7" ;;          # configure 解析成 1007，通过 >= 0.1.7
  --cflags)  echo "-I$prefix/include" ;;
  --libs)    echo "-L$prefix/lib -lusb" ;;
esac
```

注意 `AC_CHECK_TOOL` 的**交叉模式前缀**：`--build` 与 `--host` 不同时它会先找
`<host>-libusb-config`，因此 shim 需要同时提供带前缀与无前缀两个名字
（`aarch64-linux-ohos-libusb-config` + `libusb-config`）。

### 2. native 模式下 conftest 运行失败

`AutotoolsDeps` 会把依赖的 `-lusb -lusb-1.0` 放进 `LIBS`，于是 autoconf 的
"compiler works / cross compiling" 探测程序动态依赖 `libusb-1.0.so.0`，
而 configure 阶段该库不在加载器路径：

```
./conftest
Error loading shared library libusb-1.0.so.0: (needed by ./conftest)
configure: error: cannot run C compiled programs.
```

⇒ 必须使用**交叉模式**（`--build` ≠ `--host`），让 autoconf 跳过运行探测。

### 3. libtool 2.2.6 在本环境的两个产物缺陷

- `ECHO="print -r --"`：OHOS 的 `/bin/sh` 是 ksh（`print` 内建），libtool 的 echo 探测把
  ksh 专用写法写进生成的 `libtool`；而 libtool 由 profile 的 `CONFIG_SHELL`（bash）执行
  → `../libtool: line 883: print: command not found`。
  修法（与已合入的 `mecab-ko`/`openconnect`/`gts` 一致）：configure 后把生成 `libtool`
  里的 `print -rn --` → `printf %s`、`print -r --` → `printf %s\n`。
- `old_archive_cmds` 丢转义：生成的 `libtool` 里出现
  `old_archive_cmds='llvm-ar cru ~llvm-ranlib '`（`$oldlib$oldobjs` 为空），链接时报
  `llvm-ar: error: an archive name must be specified`。这是 **ltmain.sh(2011) 与
  autoconf 2.68 组合**下引号转义丢失的典型表现（参见仓库草稿 `DRAFT-E551` 与已合入的
  `classads`：用 `CONFIG_SHELL=/bin/sh` 重新生成 libtool）。用 `bash -x libtool ...`
  可以看到 `old_archive_cmds` 的具体塌陷过程。
- 另外依赖包 `.la` 记录 `libdir=/lib` 时会先报 `library ... was moved`（libusb 系列），
  构建前删除依赖 `.la` 可避免（`bookloupe` 先例）。

## 二、改走 CMake 后遇到的坑与修法（最终采用）

1. **依赖 `.pc` 前缀失真**：`libusb.pc` 的 `prefix` 指向发布机构建缓存目录、
   `libusb-1.0.pc` 是 `/usr/local`。`FindUSB.cmake` 默认走 pkg-config 会拿到错路径 ⇒
   配方直接用缓存变量短路：
   `LIBUSB_INCLUDE_DIR=<libusb-compat>/include`、
   `LIBUSB_LIBRARIES=<libusb-compat>/lib/libusb.a;<libusb>/lib/libusb-1.0.so`
   （0.1 兼容层是静态库，其符号引用 libusb-1.0）。
2. **CMake 4 拒绝老声明**：上游 `cmake_minimum_required(VERSION 2.6)` ⇒
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。
3. **`include()` 当 `include_directories()` 用**（2011 年的笔误，写的是目录）：
   `examples/CMakeLists.txt` 第 5 行 ⇒ 小补丁改为 `include_directories()`，
   否则示例程序（本 PR 的上游证据）无法构建。
4. **CMake 不认识 `HarmonyOS` 平台 ⇒ `UNIX` 未定义**：上游所有 install 规则都在
   `if(${UNIX})` 里，结果装出来只有 2 个 `.pc`（库和头都没装）⇒ 传 `-DUNIX=TRUE`。
5. **`LIB_SUFFIX=64`**：上游对 64 位目标强制把库装进 `lib64/`，与 Conan 的
   `cpp_info.libdirs=["lib"]` 不一致 ⇒ 小补丁固定 `LIB_SUFFIX` 为空。
6. **示例程序的相对 DT_NEEDED**：构建树里 `find_all` 记录的 NEEDED 是
   `../src/libftdi.so`，必须在其所在目录并以 `LD_LIBRARY_PATH=<build>/src:<libusb>/lib`
   运行（`find_all` 无硬件时打印 0 台并 exit 0，是很好的"无硬件也可跑"的上游证据）。
7. **公共头传播**：`ftdi.h` 首行 `#include <usb.h>` ⇒
   `self.requires("libusb-compat/0.1.7", transitive_headers=True, transitive_libs=True)`
   + `cpp_info.requires`；否则消费者报 `'usb.h' file not found`。

## 三、适用边界

- "该选 CMake 还是 autotools"没有普适答案：若上游 CMake 很久不维护（如本例 2011 年）
  反而可能踩老 CMake 语法/上游假设的坑，但每个坑都是"一行缓存变量或一个小补丁"级别，
  而 autotools 的坑（工具缺失、运行探测、libtool 转义）在 CI 里更难定位。
- `*-config` shim 适用于任何"configure 期依赖 `*-config` 工具、而 Conan 包只给
  pkg-config"的老工程（libusb 0.1 系、libftdi 0.x、gtk-config 时代工程）。
- 判断 libtool 产物是否已损坏的两个快速检查：
  `grep -m1 '^ECHO=' libtool`（出现 `print -r --` 即需修）与
  `grep -m1 'old_archive_cmds=' libtool`（出现空 `$oldlib$oldobjs` 即需修）。

## 验证

```sh
conan create archives/l/libftdi/0.20 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# rc=0
# 上游：examples/find_all（真机）exit 0 —— Number of FTDI devices found: 0
# 消费者：8/8 断言（上下文生命周期/枚举/失败打开的错误串/list_free 置空）
```

## 附：不要在上游 PR 中携带 `config.sub`/`config.guess` 全文

同批适配中 libart-lgpl 的 PR 最初携带 `config.sub`(2364 行)+`config.guess`(1818 行)，
平台 AI 检视直接跳过（"本次变更过大……超出处理范围"），评审门禁拿不到结论。正确做法是给
上游自带 `config.sub` 加 16 行早退分支（`archives/a/a52dec` 先例）并显式传
`--build`/`--host`。

## 相关

- `DRAFT-E551`（CONFIG_SHELL=bash 时 ltmain.sh 丢失引号转义）与本条第一节(3) 同源；
- 已合入先例：`archives/m/mecab-ko`、`archives/o/openconnect`（libtool ECHO）、
  `archives/b/bookloupe/2.0`（删除依赖 `.la`）、`archives/c/classads`（CONFIG_SHELL=/bin/sh）；
- E007（config.sub/config.guess 不识别/不可用）、E011（HMDFS 上 umask 077 临时目录不可写）
  在 autotools 路径同样适用。
