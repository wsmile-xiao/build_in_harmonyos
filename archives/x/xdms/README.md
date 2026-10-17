# xdms — OpenHarmony 编译档案

## 软件简介
xDMS（Portable DMS archive unpacker）是 Amiga **DMS（Disk Masher System）** 归档
的解包工具，由 Andre Rodrigues de la Rocha 编写、Heikki Orsila 维护，**Public Domain**。
它把 `.dms` 压缩磁盘映像还原为原始 `.adf` 映像，并支持：

| 命令 | 功能 |
|------|------|
| `xdms t <file>` | 测试归档完整性 |
| `xdms u <file> [+out]` | 解包为磁盘映像 |
| `xdms z <file> [+out]` | 解包并 gzip 压缩 |
| `xdms x <file>` | 借助 readdisk 提取归档内文件 |
| `xdms v <file>` | 查看归档信息 |
| `xdms f <file>` | 查看完整信息（逐磁道） |
| `xdms d <file>` | 显示随包 FILEID.DIZ |
| `xdms b <file>` | 显示随包 Banner |

本次适配上游发布版 **1.3.2**。命令字母大小写不敏感（`tolower(argv[i][0])`）。

## OHOS 适配要点
- **构建系统**：上游 `configure` 是手写 `/bin/sh` 脚本（**非 autoconf**），用 `sed`
  把 `{CC} {ARCHFLAGS} {ARCHLIBS} {VERSION} {PREFIX}` 替换进 `Makefile.in` 与
  `src/Makefile.in`。它**只接受 `--prefix=` 一个参数**，传其它参数会打印
  "configure parameter error" 并退出，因此不能使用 `AutotoolsToolchain`
  （它会注入 `--host` / `--build` 等）。conanfile 手工调用：
  `CC=<clang> bash ./configure --prefix=<pkg>` 然后 `make CC=<clang>`。
- **可移植性修复（关键）**：上游 1.3.2 **在现代工具链上根本链接不过**——
  `src/cdata.h` 对 `__GNUC__` 定义 `#define INLINE inline`（plain C99 `inline`），
  而 `u_heavy.c` 中 `decode_c()` / `decode_p()` 在**定义之前被调用**，编译器无法
  内联，遂发出外部引用；plain `inline` 又不产生外部定义，于是：

  ```
  undefined reference to `decode_c'
  undefined reference to `decode_p'
  ```

  该问题在 x86-64 glibc 上用 **gcc 与 clang 均可复现**，属**现代工具链回归**
  （上游 2006 年发布，GCC < 5 默认 `-std=gnu89` 时 plain `inline` 会发出外部定义；
  GCC 5 起默认 `-std=gnu11`，行为改变），**并非 OHOS 特有问题**。
  最小修复：`INLINE` → `static inline`，恢复文件内局部函数语义，不改变运行行为。

## 依赖关系
- 无编译期/运行期第三方依赖（仅 C 运行时）
- 被依赖: 无（独立 CLI 工具）

## 上游测试
上游 **没有测试目标，也没有测试目录**：

- `Makefile.in` 目标：`xdms`、`clean`、`install`
- `src/Makefile.in` 目标：`.c.o`、`xdms`、各 `.o` 依赖规则、`clean`
- 不存在 `tests/`、`test/`、`testing/`、`regression/` 目录
- `xdms.txt` 中的 "test" 指工具自带的 `xdms t` 子命令，不是测试套件

因此如实申报 **upstream_total = 0**。功能验证放在 `test_package/`：用 xDMS 自身的
CRC 例程构造一个真实可解码的 NOCOMP DMS 归档，做端到端解包并逐字节比对。

## 参考资料
- [xDMS 官方主页](http://zakalwe.fi/~shd/foss/xdms)
- [xdms-1.3.2.tar.bz2](https://zakalwe.fi/~shd/foss/xdms/xdms-1.3.2.tar.bz2)
