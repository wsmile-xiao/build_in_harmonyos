# linbox 1.7.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
LinBox —— 精确线性代数库（整数/有限域上的行列式、秩、解方程、Smith 标准形等），
产出 `liblinbox.so`。是 SageMath / passagemath 计算代数栈的顶层聚合库：
它把 givaro、fflas-ffpack、ntl、flint、iml、openblas、gsl、mpfr、gmp 串在一起。

## 三个坑，都不是「编不过」而是「看起来没关系的地方炸」

### 1）configure 在 out-of-source 构建下把 `doc` 建成了普通文件

`configure` 第 19573 行无条件执行 `cp ${srcdir}/doc/mainpage.doxy doc/`，
而此时 out-of-source 构建目录里 `doc/` 还没建出来（`config.status` 稍后才建）。
**鸿蒙的 `cp` 忽略末尾斜杠**，于是创建了一个名为 `doc` 的**普通文件**（内容就是那份 `.doxy`）。
随后 `config.status` 要建 `doc/Makefile` 就撞上：

```
mkdir: 'doc': File exists
rm: doc/Makefile: Not a directory
config.status: error: could not create doc/Makefile
```

`--disable-doc` 管不到这段（它在 `AC_OUTPUT` 之前无条件执行）。修法：configure 之前先 `mkdir -p doc`。

### 2）依赖 mpfr **必须用 4.2.2.1**

`mpfr/4.2.2` 装出的 `libmpfr.la` 里 `dependency_libs` 被烤成了 `//lib/libgmp.la`
（conan 按 `prefix=/` 构建），链接 `liblinbox.la` 时 libtool 顺着它递归解析并失败：

```
libtool: error: cannot find the library '//lib/libgmp.la' or unhandled argument '//lib/libgmp.la'
```

试过把生成的 `libtool` 里 `link_all_deplibs` 改成 `no`——**无效**（补丁确实写进去了，报错一字不变；
libtool 是在解析 `-lmpfr` 命中的 `.la` 时就展开 `dependency_libs`，与该开关无关）。
只能用补删了 `.la` 的 `mpfr/4.2.2.1`。

### 3）`__udivti3` —— 编译链接全过，**加载时才炸**

```
Error relocating .../liblinbox.so.0: __udivti3: symbol not found
```

`__udivti3` 是 128 位无符号整数除法的**编译器内建**（givaro recint / fflas-ffpack 的
`__int128` 路径会用到）。libtool 建共享库时没把 compiler-rt 的 builtins 归档链进去。

加 `-rtlib=compiler-rt` **无效**——libtool 不认这个选项，直接丢掉。
修法是把归档的绝对路径塞进链接行，路径向 `clang --print-libgcc-file-name` 要，
**不写死 SDK 版本号**（设备上是 `ohos-sdk_26.0.0.18`，别的机器未必同版）。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 4 条**真实计算断言**全绿：

```
linbox: det=-2/rank=2 通过；秩亏阵 det=0/rank=1 通过
```

- `A = [[1,2],[3,4]]`：`det(A) == -2`、`rank(A) == 2`
- `B = [[1,2],[2,4]]`（两行成比例）：`det(B) == 0`、`rank(B) == 1`

四条都可手算核对。这个测试等于**验整条依赖链**——LinBox 的 `det`/`rank` 会下沉到
givaro 的域运算、fflas-ffpack 的 BLAS 路径与 GMP 大整数。

顺带一提：`Givaro::Integer` **没有 `get_str()`**，只重载了 `operator<<`，打印要走 iostream。
