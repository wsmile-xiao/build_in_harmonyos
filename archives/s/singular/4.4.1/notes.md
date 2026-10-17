# singular 4.4.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
Singular —— 交换代数 / 代数几何 / 奇点论的计算机代数系统，
产出 `libSingular.so` 等库与 `bin/Singular`。
是 SageMath / passagemath 计算代数栈中多项式与 Gröbner 基运算的后端。

## 三个坑

### 1）`AX_PROG_CC_FOR_BUILD` 用 `_FOR_BUILD` 变量族，却混用了普通的 `$LIBS`

子包 omalloc 的 configure 里有**第二处**编译器可用性检查（`configure:20017`），
来自 `AX_PROG_CC_FOR_BUILD` 宏：

```
ac_link='$CC_FOR_BUILD -o conftest $CFLAGS_FOR_BUILD $CPPFLAGS_FOR_BUILD \
         $LDFLAGS_FOR_BUILD conftest.c $LIBS'
```

注意末尾是**普通的 `$LIBS`**（我们设过，一长串 `-lflint -lcddgmp -lgmp …`），
而 `$LDFLAGS_FOR_BUILD` 没人设 → **一个 `-L` 都没有**。于是：

```
ld.lld: error: unable to find library -lflint
ld.lld: error: unable to find library -lgmp
… （十几条）
configure: error: C compiler cannot create executables
```

最后那句报错极具误导性——听着像工具链坏了，实际只是缺搜索路径。
本包是原生构建（build == host），把同一份 `-L` 也给 `LDFLAGS_FOR_BUILD` 即可。

**排查提示**：`configure:NNNNN` 是 **configure 脚本的行号**，不是 config.log 的行号。
omalloc 的 configure 有 25439 行，两处「checking whether the C compiler works」
分别在 3733（普通 `AC_PROG_CC`，会通过）与 20017（`_FOR_BUILD`，失败）。
只抓第一处会得出「编译器没问题」的错误结论。

### 2）依赖 mpfr 必须用 4.2.2.1
`mpfr/4.2.2` 装出的 `libmpfr.la` 里 `dependency_libs` 烤死了 `//lib/libgmp.la`，
链接 `libsingular_resources.la` 时报：

```
libtool: error: '//lib/libgmp.la' is not a valid libtool archive
```

### 3）`make install` 卡在 toybox 的 `tar -j`
`Makefile.am` 的 `install-data-local` 用 `tar -jx` 解 `doc/doc.tbz2`，
而鸿蒙的 `tar` 是 toybox 的、没有 bzip2 applet：

```
toybox: Unknown command toybox
tar: had errors
mv: bad .../singular.info: No such file or directory   → install 整体失败
```

该 target 由 `if test -e $(srcdir)/doc/doc.tbz2` 保护，**删掉这个文档压缩包整段跳过**，
不必打补丁。我们本来就 `--disable-doc`，不装文档无损失。

### 另：去掉对环境 LDFLAGS 的依赖
`generate()` 里把依赖 libdir **前置**到 LDFLAGS。设备与 CI worker 的 `~/.zshrc` 都导出了
`-L$HOME/usr/local/lib`，而 conan 对 LDFLAGS 用 append、自己的 `-L` 排在其后，
链接器按顺序取第一个命中的目录就可能抢走 `-l` 的解析（ecl 实撞 libffi）。

## 真机验证（2026-08-13，HarmonyOS PC MateBook）
`conan create` 通过（用 CI 的 profile、且**保留**环境 LDFLAGS 跑的），
test_package 3 条**真实计算断言**全绿：

```
singular: Q[x,y] 上 x*y 得单项式、次数(1,1) 通过
```

- `siInit` 起 Singular 内核
- `rDefault(0, 2, {"x","y"})` 建有理数域上的二元多项式环 Q[x,y]
- `pp_Mult_qq(x, y)`：断言乘积**项数 == 1**（是单项式），
  且 x 与 y 的**指数各为 1**

走的是 Singular 真正的多项式表示与乘法内核，不是加载探针。
