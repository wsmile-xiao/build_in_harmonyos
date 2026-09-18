# E5xx: libtool -nostdlib 链接丢失 clang_rt.builtins（aarch64 fp128 软浮点符号未定义）

## 场景

OHOS aarch64 上用 autotools/libtool 构建共享库（如 zimg/libzimg 3.0.6，PR #10438，任务 #13534）。

## 症状

- `conan create` / `make` 全绿，上游测试全过（unit_test 是可执行程序，正常链接 builtins）
- `test_package` 运行时（或设备 dlopen）报：
  ```
  Error relocating .../libzimg.so.2: __addtf3: symbol not found
  Error relocating .../libzimg.so.2: __multtf3: symbol not found
  ...（__subtf3/__divtf3/__netf2/__eqtf2 同族）
  ```
  进程 exit 127。

## 根因

1. OHOS clang 包装器给 libtool 的共享库链接注入 `-nostdlib`（libtool `archive_cmds` 展开含 `-nostdlib`），禁用 clang 驱动隐式链接的 `libclang_rt.builtins.a`
2. aarch64 上 C++ `long double` 是 128 位 fp128，运算编译为 compiler-rt 软浮点内置函数（`__addtf3` 系）
3. 模板实例化 `long double` 的代码（zimg `matrix.cpp` 的 `RowMatrix<long double>`）进入 .so 后，这些符号未定义
4. `-shared` 链接期不报未定义符号错误 → 问题延迟到运行时加载才爆发；链接可执行程序不走 `-nostdlib` → 测试程序全绿，形成"测试全过但 so 带病"的隐蔽形态

## 修复

LDFLAGS 追加 `-lclang_rt.builtins`（clang_rt 目录已在包装器的 -L 搜索路径中）：

```python
# conan 配方 generate()（AutotoolsToolchain 之后）
if self.settings.os == "OHOS":
    try:
        tc.extra_ldflags.append("-lclang_rt.builtins")
    except Exception:
        tc.ldflags.append("-lclang_rt.builtins")
```

## 验证

```bash
nm -D .libs/libfoo.so | grep -cE " U __(add|sub|mul|div)tf3|__n?etf2"   # 修复后应为 0
```

## 关联

- 实例：libzimg 3.0.6（archives/l/libzimg/3.0.6，conanfile.py generate() 内实现）
- 区别于 E190（Perl XS 场景的 -nostdlib 处理，路径不同）
