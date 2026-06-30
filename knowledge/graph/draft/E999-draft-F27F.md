# E999: mimalloc MI_OVERRIDE 导致段错误

## 现象

在鸿蒙系统上编译 mimalloc 并运行测试时，所有测试程序出现段错误（Segmentation fault），进程被 killed（SIGKILL）：

```
Running tests...
    Start 1: test-api
1/4 Test #1: test-api .........................***Exception: SegFault  0.06 sec
    Start 2: test-api-fill
2/4 Test #2: test-api-fill ....................***Exception: SegFault  0.03 sec
    Start 3: test-stress
3/4 Test #3: test-stress ......................***Exception: SegFault  0.03 sec
    Start 4: test-stress-dynamic
4/4 Test #4: test-stress-dynamic ..............***Failed    0.07 sec

0% tests passed, 4 tests failed out of 4
```

手动运行测试程序：
```
$ ./mimalloc-test-api
进程退出，代码 killed
```

## 根因分析

mimalloc 的 `MI_OVERRIDE` 选项（默认 ON）会尝试覆盖系统标准的 `malloc/free/realloc` 等函数，通过符号拦截或 LD_PRELOAD 方式实现。

但在鸿蒙系统上：
1. 鸿蒙使用 musl libc，其内存管理机制与标准 glibc 不同
2. 鸿蒙的安全机制对内存分配器的替换操作有严格限制
3. 当 mimalloc 尝试覆盖系统 malloc 时，会触发安全检查或与内核内存管理冲突，导致 SIGKILL

## 解决方案

### 方案 1：禁用 MI_OVERRIDE（推荐）

在 CMake 配置时显式禁用 `MI_OVERRIDE`，将 mimalloc 作为独立库使用，而非系统 malloc 替代：

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DMI_LIBC_MUSL=ON \
      -DMI_OVERRIDE=OFF \
      ..
make -j2
make install
```

### 方案 2：仅使用静态库

如果需要更好的性能，可以只使用静态库版本：

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DMI_LIBC_MUSL=ON \
      -DMI_OVERRIDE=OFF \
      -DMI_BUILD_SHARED=OFF \
      -DMI_BUILD_STATIC=ON \
      ..
```

## 验证方法

编译完成后运行测试：

```bash
cd build
./mimalloc-test-api
# 应看到所有测试通过
# test: malloc-aligned9a...  ok.
# test: malloc-zero...  ok.
# ...
# succeeded: 37
# failed   : 0
```

## 适用软件

- mimalloc (所有版本)
- 使用 mimalloc 作为依赖的软件（需在构建配置中传递 MI_OVERRIDE=OFF）

## 注意事项

1. **不要使用 LD_PRELOAD 方式**：即使编译时禁用了 MI_OVERRIDE，也不要尝试通过 `LD_PRELOAD=/usr/lib/libmimalloc.so` 方式动态覆盖，这同样会触发段错误。

2. **链接方式**：程序需要显式链接 mimalloc 库：
   ```bash
   gcc myapp.c -lmimalloc
   ```

3. **性能影响**：禁用 MI_OVERRIDE 不会影响 mimalloc 的核心性能，只是不能自动替换系统 malloc。程序需要显式调用 mimalloc API 或链接时使用 `-lmimalloc`。

## 相关知识

- E007: config.guess 平台识别（Autotools）
- 鸿蒙系统的 SELinux 和安全机制
- musl libc 与 glibc 的差异