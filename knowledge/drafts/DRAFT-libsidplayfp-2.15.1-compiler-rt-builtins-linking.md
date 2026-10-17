# DRAFT: aarch64 上共享库缺失 compiler-rt builtins 辅助符号（__powidf2 等）

- **library**: libsidplayfp 2.15.1
- **date**: 2026-09-08
- **gate**: 上游 make check / 运行时重定位 / conan test_package
- **status**: UNMATCHED draft (路径 B 候选)

## 问题

OHOS aarch64 上由 libtool 生成的共享库在运行时重定位失败：

```
Error relocating /storage/Users/currentUser/tmp/libsidplayfp-2.15.1/src/.libs/libsidplayfp.so.6: __powidf2: symbol not found
FAIL TestPSID (exit status: 127)
FAIL TestMUS (exit status: 127)
```

链接期不报错，但直接运行测试二进制或 dlopen 该 .so 时，动态加载器立即报
`Error relocating <lib>: <symbol>: symbol not found`。

## 根因

aarch64 上 clang 将 long double / 内置 pow 等运算编译为对 compiler-rt builtins
运行时辅助符号（`__powidf2`、`__addtf3` 等）的调用。libtool 链接 `.so` 时使用
`-nostdlib` 并只显式链接 libc/libc++/unwind，未包含 compiler-rt builtins 归档，
因此生成的 `.so` 携带未定义辅助符号。这些符号在链接可执行文件时才被解析，所以
链接阶段静默通过；一旦运行期加载 `.so` 即触发重定位错误（exit 127）。

## 方案

在 conanfile.py `generate()` 中通过 AutotoolsToolchain 追加：

```python
tc.extra_ldflags.append("-lclang_rt.builtins")
```

等价手段：configure 时传 `LDFLAGS="-L<clang rt dir> -lclang_rt.builtins"`，
rt 目录为 OHOS SDK 的 `.../llvm/lib/clang/<ver>/lib/aarch64-linux-ohos/`。

## 验证

- 修复前：`nm -D <built>.so | grep __powidf2` 无输出；make check 中
  TestPSID/TestMUS exit 127。
- 修复后：本地 `make check` 8/8 PASS（含此前失败的 TestPSID/TestMUS）；
  conan-verify G2 conan create + test_package 消费者测试通过。

## 适用边界

- 命中：aarch64 OHOS 上 libtool 管理的 autotools/C++ 包，代码路径含 long double
  或内置 pow 运算，生成 .so。
- 不命中：静态链接（.a）消费者；cmake 构建（clang 默认链 compiler-rt）。
- 已知先例：仓库内 adplug 2.4 配方注释记录同款问题（`__addtf3`），亦用
  `-lclang_rt.builtins` 解决，证实跨库可复用。

## 反例与限制

- 若链接错误为 `undefined reference to '__powidf2'`（链接期即报），是
  可执行文件/测试二进制直接缺 builtins，同样加 `-lclang_rt.builtins` 可解。
- 不要把该错误误判为库源码缺陷；先查辅助符号来源。
