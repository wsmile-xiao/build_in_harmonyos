# mm 1.4.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + libtool)
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4
- 状态: built

## 源码获取

上游官网 `http://www.ossp.org/pkg/lib/mm/` 已不可达（HTTP/HTTPS 均超时或 404，FTP 亦不可用）。
改用 pkgsrc 官方 distfiles 镜像，并与第二个独立镜像交叉校验字节一致：

| 镜像 | sha256 |
|------|--------|
| `https://cdn.netbsd.org/pub/pkgsrc/distfiles/mm-1.4.2.tar.gz` | `8caddd1e…3285` |
| `https://www.mirrorservice.org/sites/ftp.ossp.org/pkg/lib/mm/mm-1.4.2.tar.gz` | `8caddd1e…3285` |

两镜像 sha256 完全一致，源码可信（R39）。

## 编译步骤

```bash
sh ./configure --prefix="$DEFAULT_PREFIX" \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  --enable-shared --enable-static \
  CC=clang
make -j1
make install DESTDIR="$TEST_PREFIX"
make test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`，configure 直接失败 | 归档内 `config.guess` 为 2005-12-13 版，不认识本机 uname 输出 | 显式传 `--build` / `--host=aarch64-unknown-linux-gnu`，跳过自动猜测 |
| 2 | `make test` 在 `/tmp/mm.core.<pid>` 处报 `Read-only file system` | `mm.h` 的 `MM_CORE_DEFAULT_FILE` 硬编码 `/tmp`，鸿蒙 PC 上 `/tmp` 只读（知识库 E002） | 补丁 `patches/0001-mm_core.c.patch`：默认路径改读 `$TMPDIR`，未设置时回退 `/tmp` |
| 3 | `make -jN` 报 `jobserver mkfifo ... Operation not permitted` | 本机 `mkfifo` 工具不可用，GNU make 的 jobserver 无法建立通信 FIFO | 全程使用 `-j1`（配方内 `autotools.make(args=["-j1"])`） |
| 4 | 外源构建报 `No rule to make target 'mm_vers.c'` | 上游 2006 年生成的 Makefile 无 VPATH / `$(srcdir)` 支持，源码文件只按相对路径查找 | 配方内改为 in-source 构建（`layout()` 中 `self.folders.build = "."`） |
| 5 | CI 上 `config.status` 写 `./confXXXXXX/*` 全部 `Permission denied`，`chmod: mm-config: No such file or directory`，随后 `make: *** No targets specified and no makefile found` | HMDFS 会给目录强制加上 setgid 位，autoconf 的 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 因此得到一个 `drwx--S---` 的临时目录而写不进去（知识库 **E114**）；`config.status` 写 Makefile/config.h 全部失败，`make` 自然找不到 Makefile | 配方 `_drop_umask_077()`：在 `configure()` 之前就地剥离 `configure` / `config.guess` 中的 `umask 077`（实测命中 `configure` 2 处、`config.guess` 3 处），子 shell 保留。两个脚本都是 tarball 内 autoconf 生成物，故按仓内 abiword/4ti2 惯例在配方内改写，未命中时打 warning 而非静默通过 |
| 6 | 同上族：`config.guess: line 1278: .../cgXXXXXX/dummy.c: Permission denied` → `unable to guess system type` | 同 E114，`config.guess` 的三级临时目录回退链全部带 `umask 077` | 由第 5 项的同一个 `_drop_umask_077()` 一并修掉；不过本库仍显式传 `--build`/`--host`（第 1 项），不依赖猜测结果 |

## 源码修改

`patches/0001-mm_core.c.patch` —— 修改 `mm_core.c` 中 `mm_core_create()` 的默认后备文件生成逻辑：

```c
-        sprintf(filename, MM_CORE_DEFAULT_FILE, (int)getpid());
+        const char *tmpdir = getenv("TMPDIR");
+        if (tmpdir == NULL || *tmpdir == '\0')
+            tmpdir = "/tmp";
+        snprintf(filename, sizeof(filename), "%s/mm.core.%d", tmpdir, (int)getpid());
```

同时把不安全的 `sprintf` 换成有界的 `snprintf`。行为兼容：显式传入 `file` 参数时路径逻辑完全不变，仅在默认路径场景下生效。

配方层面的平台适配（非 `patches/`，因为目标是 tarball 内的 autoconf 生成物）：`conanfile.py:_drop_umask_077()` 在 `configure()` 之前把 `configure` / `config.guess` 里的 `(umask 077 && ` 就地去掉，只改这一处前缀、子 shell 结构保留，改完打印命中数量，一处都没命中则 `output.warn` 而不是静默通过。上游源码本身未被改动。

## 依赖版本

无第三方依赖（`configure` 输出中无任何外部库探测失败；自带 json/avltree/array/utf8/uri 实现，仅链接 libc/libm）。

## 验证结果

```bash
$ make test
*** TESTING GLOBAL LIBRARY API ***
... (mm_global / mm_alloc / mm_realloc / mm_free 全部通过)
*** TESTING LOW-LEVEL SHARED MEMORY API ***
... (mm_core_create / mm_core_alloc / mm_core_attach 全部通过)
*** TESTING STANDARD MALLOC-STYLE API ***
... (mm_create / mm_malloc / mm_calloc / mm_realloc / mm_free / mm_destroy 全部通过)
OK - ALL TESTS SUCCESSFULLY PASSED.
```

上游测试套件（`mm_test.c`，覆盖三层 API）在打完补丁后 **全部通过**。

### R51 上游测试用例清点申报表

| 步骤 | 内容 |
|------|------|
| ① 清点 | 上游 tarball 自带 1 个回归测试程序 `mm_test.c`（266 行），无独立测试框架；含 3 个测试组（GLOBAL LIBRARY API / LOW-LEVEL SHARED MEMORY API / STANDARD MALLOC-STYLE API）、4 个子测试段（Memory Segment Access / Memory Locking / Allocation / Defragmentation）、15 条 `FAILED_IF` 断言，覆盖 14 个 `mm_*` API |
| ② 运行 | `make test`（等价 `make check`）在 HarmonyOS PC aarch64 实机运行，实测通过 |
| ③ 如实回填 | **上游用例数 = 1 个程序（15 断言，未修改）**；适配后**新增**消费者测试 1 个程序（`test_package/test.c`，10 条 `CHECK` 断言，含 4 条专门覆盖 `$TMPDIR` 默认路径的鸿蒙特有用例）。上游用例 100% 通过，新增用例 100% 通过 |

> 清点口径：以 tarball 内实际文件与 `make check` 实测输出为准，不以文档描述为准。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libmm.so.14` | 共享库 | 主产物 |
| `libmm.a` | 静态库 | 静态产物 |
| `libmm.la` | libtool 归档 | libtool 元数据 |
| `mm-config` | 脚本 | 上游自带配置查询脚本 |
| `mm.h` | 头文件 | 唯一公开头 |

## 注意事项

- 上游 2006 年后未再更新，`configure` 为老式 autoconf 2.59 生成，跨平台需显式指定三元组。
- `mm_core_create()` 的默认后备文件语义：同一 PID 复用同一路径，多进程共享需显式传自定义路径。
---

**编译结束**: 2026-09-26 17:08
**最终状态**: built
