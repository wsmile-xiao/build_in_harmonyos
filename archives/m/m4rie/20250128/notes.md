# m4rie 20250128 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
m4rie 是 **GF(2^e)** 上的稠密矩阵运算库（m4ri 只做 GF(2)）。
是 SageMath / passagemath 的 `passagemath-m4ri-m4rie` 发行包的底层依赖。

## 关键适配：`-Llib` 相对路径会让 libtool 直接失败

构建曾报：

```
./libtool: line 7733: cd: lib: No such file or directory
libtool: error: cannot determine absolute directory name of 'lib'
make[1]: *** [Makefile:596: libm4rie.la] Error 1
```

报错指向 libtool，实则是 `LDFLAGS` 里混进了一个**相对路径** `-Llib`：

```
LDFLAGS = -L<m4ri>/lib -L<libpng>/lib -Llib -L$HOME/usr/local/lib
                                       ↑↑↑↑
```

来源是 recipe 里"把 conan 依赖 libdir 前置到 LDFLAGS"那段——
**被 skip 的传递依赖（无 package_folder）其 `cpp_info.libdirs` 会退化成相对的 `"lib"`**，
原样拼进去就成了 `-Llib`。修法是只取绝对路径：

```python
_Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
               for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
```

该过滤已下沉到 conan-packager 生成器的 autotools / meson 模板，新 recipe 天生带上。

**证伪的一条**：曾以为要补 `--with-m4ri=<prefix>`，实测**不需要**——
生成的 Makefile 里 `M4RI_CFLAGS` / `M4RI_LIBS` 已由 pkg-config 正确填好，
m4ri 本来就找得到，加了也不改变结果。故最终 recipe 不含该参数。

其余：删除 `lib/*.la`。源码取自 SageMath 的 `checksums.ini`，sha256 已核对。

## 真机验证（2026-08-13，HarmonyOS PC MateBook）
用 **CI 的 profile、且保留环境 LDFLAGS** 跑 `conan create`，
test_package 真实计算断言全绿：

```
m4rie: GF(4) 上 I*B==B 逐元素通过；元素读写自洽 通过
```

- 以 `x²+x+1`（`0b111`）为不可约多项式构造 **GF(4)**
- `mzed_mul` 算 `I · B`，**逐元素**比对结果 == B
- 校验 `mzed_write_elem` 写入的 GF(4) 元素能被 `mzed_read_elem` 原样读回

走的是 m4rie 区别于 m4ri 的 **GF(2^e)** 路径，不是 GF(2)。
