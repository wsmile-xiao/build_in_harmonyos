# radare2

逆向工程框架，用于分析、调试、逆向二进制文件。

## 特性

- 多架构支持（x86, ARM, MIPS 等）
- 反汇编、调试、模拟执行
- 插件扩展系统
- 脚本支持（Python, JavaScript 等）

## 依赖

- capstone（反汇编引擎，可选但推荐）

## 编译

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

或使用 meson：

```bash
meson setup build --prefix=$DEFAULT_PREFIX
meson compile -C build
meson install -C build --destdir=$TEST_PREFIX
```
