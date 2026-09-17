# E577 — 纯 Makefile 三方库配方的三个打包陷阱

- **草稿 ID**: E577（draft，待主编审核 promote）
- **来源**: libfilteraudio/0.0.1 HarmonyOS PC（OHOS aarch64）适配，2026-09-15
- **分类**: conan / make / build-system / linking / relocatable
- **触发面**: `error_signature` 只覆盖第 1 个陷阱（有明确报错）；第 2、3 个是**静默产物缺陷**，
  没有错误日志，只能靠产物审查发现，故在本文给出可执行判据。

## 陷阱 1：`basic_layout()` 的构建目录里没有 Makefile（有明确报错）

**现象**（conan create 真实输出，`conan-create.log`）：

```
libfilteraudio/0.0.1@ohpcd/stable: RUN: make -j1 CC=/data/service/hnp/bin/clang
make: *** No targets specified and no makefile found.  Stop.
libfilteraudio/0.0.1@ohpcd/stable: ERROR:
Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' build failed
```

**根因**：Conan 2 的 `basic_layout(self)` 把 `folders.build` 设为 `build-<build_type>`
（实测 `build-release`），而 `self.run()` 的默认 cwd 是 build folder；源码被解压到 base/source
folder（与 build folder 不同层），纯 Makefile 项目在那里找不到 `Makefile`
（报错目录里只有 `conan/` 子目录）。

**修复（推荐，实测通过）**：

```python
def layout(self):
    basic_layout(self, build_folder=".")   # 等价写法: basic_layout(self); self.folders.build = "."
```

`build_folder="."` 让 build folder 压回源码根，`make` 直接命中 Makefile。
仓库内先例：`archives/a/abduco/0.6/conanfile.py` 用 `self.folders.build = "."`。

**回退**：不改 layout，在 `self.run(..., cwd=self.source_folder)` 里跑 make
（`DRAFT-cd-hit-4.8.1-make-conan-recipe` 的做法）。

## 陷阱 2：`make install` 的替换把 `.pc` 的 prefix 固化成构建目录（静默）

**现象**：包内 `lib/pkgconfig/<name>.pc` 的 `prefix=` 不是包路径，而是**构建目录死路径**：
上游 install 规则写成

```make
@pc_file=.../pkgconfig/filteraudio.pc ;\
sed -e 's:__PREFIX__:'$(abspath $(PREFIX))':g' $$pc_file > temp_file && mv temp_file $$pc_file
```

Conan 配方的标准做法是 `make install DESTDIR=<package_folder> PREFIX=`（PREFIX 留空以落成
`<pkg>/include` + `<pkg>/lib`）。此时 `$(abspath $(PREFIX))` = `$(abspath "")` = **当前目录**
（构建目录），于是 `.pc` 里带着一个打包机上的死路径——符合 R49 所指的
「包内 .pc 的 prefix 固化打包机路径」这一类缺陷。

**判据（无需报错即可检出）**：

```sh
PKG=$(conan cache path "<pkg>/<ver>@<user>/<channel>:<package_id>")
cat "$PKG"/lib/pkgconfig/*.pc | head -3
PKG_CONFIG_PATH="$PKG/lib/pkgconfig" pkg-config --cflags --libs <name>
```

修复前 `--cflags` 会打印构建目录下的 `-I.../b/...`；修复后打印包内相对解析出的路径。

**修复（推荐）**：`package()` 里在 `make install` 之后重写 `.pc` 为可重定位写法
（与 `archives/a/abiword-plugin-*/conanfile.py` 同款）：

```
prefix=${pcfiledir}/../..
libdir=${prefix}/lib
includedir=${prefix}/include
```

实测（libfilteraudio 0.0.1）：

```
$ PKG_CONFIG_PATH=$PKG/lib/pkgconfig pkg-config --modversion filteraudio
0.0.1
$ PKG_CONFIG_PATH=$PKG/lib/pkgconfig pkg-config --cflags --libs filteraudio
-I<pkg>/lib/pkgconfig/../../include -L<pkg>/lib/pkgconfig/../../lib -lfilteraudio
```

## 陷阱 3：Makefile 的 `VERSION` 决定 soname，不能按包版本覆盖（静默）

**现象**：`libfilteraudio` 的 tag 是 `v0.0.1`，但上游 Makefile 仍写 `VERSION = 0.0.0`，
soname 由 VERSION 末段派生（`SHARED_LIB = libfilteraudio.so.$(VERSION 末段)`）→
`libfilteraudio.so.0`。若为了让「包版本与库版本一致」而传 `make VERSION=0.0.1`，
soname 会变成 `libfilteraudio.so.1`——**静默的 ABI 误声明**（没有任何报错，只有
`readelf -d` 能看出来）。

**判据**：

```sh
readelf -d "$PKG/lib/libX.so.0.0.0" | grep SONAME   # 期望: Library soname: [libX.so.0]
```

**修复（推荐）**：不改上游 VERSION，保留上游 ABI 命名（`libX.so.0.0.0` + soname `libX.so.0`
+ 相对软链 `.so.0 → .so.0.0.0`），只把**发布版本**写进 `.pc` 的 `Version:` 与 manifest/PR 文本；
并在 notes/PR 里说明「上游 Makefile VERSION 未随 tag 更新」这一事实。

## 适用范围

- 上游只有手写 Makefile（无 `configure`/`CMakeLists.txt`/`meson.build`）的 C/C++ **库**配方；
- 陷阱 1 对纯 Makefile **工具**同样成立（见 `DRAFT-cd-hit-4.8.1-make-conan-recipe`）；
- 陷阱 2/3 只在产物是库、且上游 install 规则会做文本替换 / 用 VERSION 派生 soname 时成立。

## 非适用边界

- CMake/Meson/Autotools 工程有各自的 layout 与 soname 机制，不走本条（SONAME 缺失走
  `DRAFT-libharu-2.3.0-missing-dt-soname`）；
- 上游 Makefile 用 `?=` 或 `override` 保护 VERSION 时不适用陷阱 3；
- 上游 install 规则本身就以 `$pcfiledir` 或相对路径写 `.pc` 时无需陷阱 2 的处置。

## 本次实测背景（可复核）

- 上游源码: `https://github.com/irungentoo/filter_audio` tag `v0.0.1`（commit `ada2f4fd`），
  sha256 `fb135592c5133c3b4b664da18f988f58609db912f204059abe16277df044a366`；
- 环境: OHOS aarch64 / clang 15.0.4 / conan 2.29.1 / profile `ci/conan/profiles/ohos-aarch64`；
- 复现命令与产物证据: 本任务采信轮日志 `conan-create.log`（clean 轮，`RUN: make`×5）、
  `archives/l/libfilteraudio/0.0.1/reports/conan-verify-supplement.md`（任务本地 reports/，
  不进 PR）。
