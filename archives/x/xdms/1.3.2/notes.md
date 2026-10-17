# xdms 1.3.2 适配笔记

## 软件简介
xDMS（Portable DMS archive unpacker）解包 Amiga **DMS（Disk Masher System）** 归档：
把 `.dms` 压缩磁盘映像还原为原始 `.adf` 映像，并支持测试归档完整性（`t`）、
查看归档信息（`v` / `f`）、显示随包 FILEID.DIZ（`d`）与 Banner（`b`）。
作者 Andre Rodrigues de la Rocha，维护者 Heikki Orsila，**Public Domain**。

## 编译环境
- 构建系统: makefile（上游自带手写 `configure`，**非 autoconf**）
- 目标平台: OpenHarmony OHOS / aarch64
- 编译器: clang（`aarch64-unknown-linux-ohos`）

## 编译步骤
上游 `configure` 是手写 `/bin/sh` 脚本：读取环境变量 `CC` / `CFLAGS` / `LDFLAGS`，
再用 `sed` 把 `{CC} {ARCHFLAGS} {ARCHLIBS} {VERSION} {PREFIX}` 替换进
`Makefile.in` 与 `src/Makefile.in`。它**只接受 `--prefix=` 一个参数**，传其它参数
会打印 "configure parameter error" 并退出——因此不能使用 `AutotoolsToolchain`
（它会注入 `--host` / `--build` 等）。conan 的做法：

```
CC=<OHOS clang> bash ./configure --prefix=<package_folder>
make CC=<OHOS clang> SHELL=<bash>
```

## OHOS / 现代工具链可移植性修改（在上游源码上做最小改写）

| # | 修改 | 原因 |
|---|------|------|
| 1 | `src/cdata.h`：`#define INLINE inline` → `#define INLINE static inline` | C99 的 plain `inline` **不产生外部定义**；`u_heavy.c` 中 `decode_c()` / `decode_p()` 在定义之前被调用，编译器无法内联，遂发出外部引用 → `undefined reference to 'decode_c' / 'decode_p'`，链接失败。 |

### 关于修改 1 的完整根因链

**原始失败**（在 x86-64 glibc 上，`gcc` 与 `clang` 均复现）：

```
/usr/bin/ld: u_heavy.o: in function `Unpack_HEAVY':
u_heavy.c:(.text+0x7f): undefined reference to `decode_c'
u_heavy.c:(.text+0x95): undefined reference to `decode_p'
collect2: error: ld returned 1 exit status
```

**定位**：`src/cdata.h` 第 30-44 行的 `INLINE` 宏定义。`__GNUC__` 分支给出 plain
C99 `inline`。

**根因**：C99 语义下，`inline`（不带 `static`/`extern`）只是**内联定义**，不对外
发出符号定义。`u_heavy.c` 中：

```c
INLINE USHORT decode_c(void);   /* line 33: 声明 */
...
c = decode_c();                 /* line 62: 调用 —— 早于定义 */
...
INLINE USHORT decode_c(void){   /* line 77: 定义 */
```

调用点早于定义，编译器无法内联，于是生成对 `decode_c` 的外部调用；而该 inline
定义不发出外部符号，链接器无处解析 → undefined reference。

**为何上游当年能编过**：GCC < 5 默认 `-std=gnu89`，C89/gnu89 下 plain `inline`
会同时发出外部定义。GCC 5 起默认 `-std=gnu11`，行为改变。上游 1.3.2 发布于
2006 年，因此这是一个**现代工具链回归**，与 OHOS 无关——在 Debian/Ubuntu 上用
现代 gcc/clang 编译上游原始 tarball 同样失败。

**修复**：改为 `static inline`，恢复文件内局部函数的本意语义（`decode_c` /
`decode_p` 本就只在 `u_heavy.c` 内使用）。语义等价，不改变任何运行行为。

**重编译验证**：`gcc` 与 `clang` 均链接成功，二进制可正常运行（详见验证结果）。

## 上游测试
上游 **没有任何测试目标或测试目录**：

- `Makefile.in` 目标：`xdms`、`clean`、`install`
- `src/Makefile.in` 目标：`.c.o`、`xdms`、各 `.o` 依赖规则、`clean`
- 无 `test` / `check` 目标
- 解包后 36 个文件中不存在 `tests/`、`test/`、`testing/`、`regression/` 目录
- `xdms.txt` / `ChangeLog.txt` 中的 "test" 仅指工具自带的 `xdms t` 子命令（测试归档完整性），不是测试套件

如实记录：**upstream_total = 0**。功能验证放在 `test_package`（消费者视角）。

## 打包要点
- `bin/xdms`（唯一产物）
- `share/man/man1/xdms.1`
- `share/doc/xdms-1.3.2/{xdms.txt,COPYING,ChangeLog.txt}`
- `licenses/COPYING`

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

## 注意事项
- `xdms` 的命令字母**大小写不敏感**：`tolower(argv[i][0])`，所以 `xdms Z` 等价于
  `xdms z`（解包并 gzip 压缩，需要外部 `gzip`），并非错误用法。
- 解包路径只在磁道号 < 80 且 `unpklen > 2048` 时才写出数据（`pfile.c:340`），
  构造功能测试归档时载荷必须大于 2048 字节。

<!-- notes-end -->
