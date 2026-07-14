# libkeccak 1.4.3 适配笔记

## 概况

- 上游：https://github.com/maandree/libkeccak （tag 1.4.3，ISC）
- 构建系统：POSIX Makefile（无 configure）
- 依赖：仅 libc
- 产物：`libkeccak.a`（默认）/ `libkeccak.so.1.4`（`shared=True`）+ `libkeccak.h` + `libkeccak/*.h`
- 状态：built（CI 在真实鸿蒙 worker 上执行 conan create 验证）

## 上游构建系统分析

`Makefile` 包含 `config.mk`（通用配置）与 `linux.mk`（平台配置，定义 `LIBEXT=so`、
`LIBFLAGS=-shared -Wl,-soname,libkeccak.so.1`）。目标：

- `libkeccak.a` — 静态库（`.c.o` 规则始终带 `-fPIC`，因此静态库亦可被 PIC 消费）
- `libkeccak.so` — 共享库，soname 为 `libkeccak.so.1`
- `test` / `benchmark` — 上游自测与基准程序
- `install` — 安装库、头文件、man3/man7、LICENSE

## 适配要点

### 1. CC=c99 覆盖（R33）

`config.mk` 中 `CC = c99`。Makefile 内的赋值优先级高于环境变量，因此仅通过
buildenv 传 `CC` 无效，必须命令行覆盖：

```python
executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = executables.get("c", "clang")
ar = executables.get("ar", "ar")
self.run(f'make -j1 CC="{cc}" AR="{ar}" libkeccak.a', cwd=self.source_folder)
```

编译器从 Conan profile（`tools.build:compiler_executables`）获取，不裸用 `${CC}`。

### 2. 不使用 make install

上游 `install` 目标会：

- `cp` 库文件后用 `ln -sf` 建 `libkeccak.so.1` / `libkeccak.so` 软链接 —— HMDFS 下
  `ln -sf` 不能覆盖已存在的软链接（平台陷阱）；
- 安装 man3（58 页）与 man7 手册 —— Conan 包内无需分发。

因此 `package()` 用 `conan.tools.files.copy()` 显式拷贝头文件与库文件。`shared=True`
时在 `package()` 内复刻 soname 布局：`libkeccak.so.1.4` 为实体，`libkeccak.so.1` 与
`libkeccak.so` 为软链接，创建前先 `os.remove()`（对应平台的"先删后建"规则）。

### 3. musl 兼容性

`common.h` 保留 `ALLOCA_LIMIT` 宏并在 `__GLIBC__` / `__APPLE__` 等分支下 `#include <alloca.h>`，
但 1.4.3 的 `.c` 源码实际未调用 `alloca()`（全部走 `malloc`）。其余仅用到
`<sys/stat.h>`、`<unistd.h>`、`<errno.h>` 等 POSIX 接口，无 glibc 专有 API。
**结论：musl/OHOS 下无需任何补丁。**

### 4. 静态为默认

`options = {"shared": [True, False]}`，默认 `False`。libkeccak 非系统同名库，
两种链接方式均可；默认静态可避免消费者的运行期库路径依赖，`shared=True` 时
soname 布局与上游一致。

## 验证

上游 `make check` 依赖仓库内 `.testfile` 与 `sha256sum`，属构建期自测；Conan 侧的实质验证在
`test_package/` 中完成（消费者视角，L1e 破坏性反向验证亦能覆盖）：

| 断言 | 内容 |
|------|------|
| 1 | `SHA3-256("")` = `a7ffc6f8…f8434a`（NIST 标准向量） |
| 2 | `SHA3-256("abc")` = `3a985da7…431532`（NIST 标准向量） |
| 3 | `HMAC-SHA3-256(key="key", "abc")` 计算成功且不同于裸 SHA3-256 |

本地（x86_64/aarch64 macOS，clang，`-Wall -Wextra`）用同一份 `test_package.c` 链接
`libkeccak.a` 运行，三条断言全部通过、无告警；鸿蒙 aarch64 的编译与运行由 CI 在真实
worker 上验证。

## 消费者注意事项

`libkeccak_hmac_initialise()` → `libkeccak_hmac_set_key()` 内部对 `state->key_opad`
调用 `realloc()`，因此 `struct libkeccak_hmac_state` 必须先清零再初始化，否则会 realloc
野指针导致崩溃。`test_package.c` 中已 `memset(&state, 0, sizeof(state))`。

## 未采取的做法

- 未生成任何补丁（源码在 musl 下开箱可编译，加补丁只会增加维护面）。
- 未打包 man 手册与 `benchmark`/`test` 二进制（库类型包，非 CLI 工具，故无 commands.json，R38 不适用）。

---

构建系统：POSIX Makefile（`make CC=<toolchain clang> AR=<toolchain ar> libkeccak.a`），无 configure，无补丁。
