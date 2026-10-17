# Draft: `DRAFT-XCOLMIX-107-MAKEFILE-HARDCODED-CFLAGS`
> Stem: `xcolmix-1.07-makefile-hardcoded-cflags-overrides-toolchain` — pairs with the same-stem `.kv`

# 手写 Makefile 在子 make 命令行上硬写 CFLAGS：conan 的编译标志全部失效

## 基本信息

- **ID**: DRAFT-XCOLMIX-107-MAKEFILE-HARDCODED-CFLAGS
- **严重度**: 1（看起来像"依赖没发布"，实际依赖就在图里，只是没送到编译器）
- **类别**: conan | build-system | make | dependency | linking
- **触发工具**: conan | make | clang | ld
- **阶段**: configuration → compiling → linking
- **来源**: xcolmix 1.07 适配（2026-10-03，OHOS aarch64）

## 错误特征

```
fatal error: 'forms.h' file not found
# 或
/opt/ohos-toolchain/clang -c -O2 -Wall -c -o usage.o usage.c
                                          ↑ 只有 Makefile 自带的标志，conan 缓存路径一个都没有
ld.lld: error: undefined symbol: fl_initialize
```

## 根因（一类）

GNU make 的变量优先级是 **命令行赋值 > makefile 内赋值 > 环境变量**。老式手写
Makefile 普遍把标志写死在"会再起一个子 make"的目标里：

```make
STDCFLAGS = -c -O2 -Wall $(XFINCDIR)
STDLFLAGS = -s -L/usr/X11R6/lib

final:
	make xcolmix CFLAGS="$(STDCFLAGS)" LFLAGS="$(STDLFLAGS)"

xcolmix: $(OBJ)
	$(CC) -o xcolmix.new $(OBJ) $(XFLIBDIR) -lforms -lX11 -lm $(LFLAGS)
```

父 make 从 conan 拿到的 `CFLAGS` 是**环境变量**，子 make 命令行上的 `CFLAGS=`
直接盖掉它。于是 `AutotoolsDeps` 算出来的全部 `-I/-L/-D` 一条都进不了编译行。

判别要点（30 秒定位）：**日志里 clang 的命令行若只剩 Makefile 自带的那几个标志，
而 conan 缓存路径一个都没出现，就是这个坑** —— 不要去查依赖发布（R36）。

链接行同理：上面那条规则完全不吃 `LDFLAGS`，所以 `-L` 只能走 `XFLIBDIR`。

唯一真正会自动生效的通道是 `CPPFLAGS` —— make 内建 `.c.o` 规则是
`$(CC) $(CFLAGS) $(CPPFLAGS) -c`，`AutotoolsDeps` 写的 `CPPFLAGS` 会被带上。
但这是**隐式**行为，不能作为设计依据。

## 修法

**先读 Makefile 头部注释**。老 Makefile 通常自己写明了旋钮，xcolmix 就写着：

> "Otherwise, set `XFLIBDIR` to `-L...` (the directory where the library lives)
> and `XFLIBINC` to `-I...`"

直接用它们，让上游目标原样执行：

```python
def build(self):
    apply_conandata_patches(self)
    includes = self._search_directories("includedirs")
    libraries = self._search_directories("libdirs")
    self.run("make -j1 final "
             f"XFINCDIR={' '.join(f'-I{p}' for p in includes)} "
             f"XFLIBDIR={' '.join(f'-L{p}' for p in libraries)}",
             cwd=self.build_folder, env="conanbuild")
```

要点：

1. **显式优于隐式**：仍照常 `AutotoolsToolchain` + `AutotoolsDeps` + `VirtualBuildEnv`
   （让 `CC` 来自 conf，R33），但依赖路径走上面两个变量，便于评审逐字核对。
2. **Conan 2 的 `self.dependencies.host` 给的是整个 host 闭包**，不只是直接
   `requires`。本例一次拿到 9 个包（libforms/libx11/xorgproto/xtrans/libxcb/
   libxau/libxdmcp/libxpm/libjpeg），正好覆盖 X11 协议头的归属。
3. **build() 之后必须断言产物**：读 ELF 头 + 核对 `DT_NEEDED`。
   `make` 退出码 0 不等于"链上了正确的库"。
   实测本例 `nm -D --undefined-only` 有 **43 个 `fl_*` 未定义符号**，
   `readelf -d` 显示 `NEEDED libforms.so.2 / libX11.so.6 / libc.so`。
4. **上游变量名拼错不要顺手修**：`STDLFLAGS` 被 `final` 当成 `LFLAGS` 传，
   于是链接行恒定带一个 `-L/usr/X11R6/lib`。该目录不存在，链接器忽略，无害。
   改它属与任务无关的上游改动。

## 验证

```
$ make -j1 final XFINCDIR='-I<libforms>/include -I<xorgproto>/include …' XFLIBDIR='-L<libforms>/lib …'
/opt/ohos-toolchain/clang -c -O2 -Wall -I… -c -o usage.o usage.c      ← conan 路径已进命令行
/opt/ohos-toolchain/clang -o xcolmix.new … -L… -lforms -lX11 -lm -s -L/usr/X11R6/lib
$ readelf -d <pkg>/bin/xcolmix | grep NEEDED
  (NEEDED)  Shared library: [libforms.so.2]
  (NEEDED)  Shared library: [libX11.so.6]
  (NEEDED)  Shared library: [libc.so]
```

## 适用面与检出手段

- 适用面：所有"无 configure / 无 autotools / 无 meson / 无 cmake、只有手写
  Makefile"的包 —— 1990-2000 年代的 X11 工具、编辑器、小项目。
  可搜索特征：tarball 里只有 `src/Makefile`；目标名是 `final`/`dist` 而非 `all`；
  存在 `STDCFLAGS`/`STDLFLAGS`/`XFINCDIR`/`XFLIBDIR` 这类自造变量名。
- 检出手段三条：
  1. `grep -nE '\b(CFLAGS|LFLAGS|CPPFLAGS|LDFLAGS)\s*=\s*"' <src>/Makefile`
     —— 命中即高危；
  2. `grep -nE '^\t(make|\$\(MAKE\))' -A2 <src>/Makefile`
     —— 看子 make 有没有硬写标志；
  3. 编译日志里 clang 命令行是否出现 conan 缓存路径。

## 关联

- `notes.md` §2（xcolmix 1.07 归档）
- 同类形态：`tng-1.8.2-static-zlib-priv-link-self-contained`（链接期自足性）
