# draft-mklibs-0.1.46-gnu-typeof-under-stdcxx17

## 症状

手工构建（`clang++ -DHAVE_CONFIG_H -I. -I../.. -fPIC -O2 -c elf.cpp`）成功；同一源码在
`conan create` 内失败：

```
src/mklibs-readelf/elf.cpp:99:36: error: unknown type name 'typeof'; did you mean 'typedef'?
  this->type      = convert<_data, typeof ehdr->e_type     >()(ehdr->e_type);
                                   ^~~~~~
                                   typedef
src/mklibs-readelf/elf.cpp:102:36: error: type name does not allow storage class to be specified
2 warnings and 20 errors generated.
make[3]: *** [Makefile:394: elf.o] Error 1
```

## 根因

- 上游 `elf.cpp` 使用 GNU 扩展关键字 `typeof`（共 44 处、26 行）；
- 手工构建时 clang 处于默认方言（`gnu++17`），`typeof` 可用；
- `conan create` 使用 `ci/conan/profiles/ohos-aarch64` 的 `compiler.cppstd=17`，
  AutotoolsToolchain 注入 `-std=c++17`（**非** gnu 变体），GNU 扩展关键字被禁用。

## 修复

补丁 `patches/0005-src-mklibs-readelf-elf.cpp.patch`：

```diff
-  this->type      = convert<_data, typeof ehdr->e_type     >()(ehdr->e_type);
+  this->type      = convert<_data, __typeof__ ehdr->e_type     >()(ehdr->e_type);
```

（44 处全量替换；`__typeof__` 是 GCC/Clang 的规范扩展拼写，在 `-std=c++17` 与 `gnu++17`
下均可用，语义不变。）

## 诊断启发式

「手工构建过、conan 构建挂」且错误是"未知类型/未知关键字/隐式函数声明"，优先比对
conan toolchain 注入的 `-std=` 与上游代码使用的 GNU 扩展（`typeof`、`__attribute__` 变体、
可变长数组、嵌套函数）。同类修法优先改写为标准扩展拼写（`__typeof__`），而不是放宽标准等级。

## 相关条目

- `E490`（autotools 脚本可执行位）
- `E007`（config.guess 平台识别）
