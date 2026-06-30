# atasm 1.30 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 平台: OpenHarmony aarch64 (musl libc)
- 状态: published

## 编译步骤

atasm 是纯 Makefile 项目，Makefile 位于 `src/` 子目录。无需 configure 步骤。

1. 下载源码 tarball（因 SSL 证书问题，使用 `curl -k` 手动下载）
2. 解压并初始化编译环境（`ohc-run.py init-build --no-download`）
3. 修改 `src/Makefile`：禁用 zlib、CC 改为 clang、调整 CFLAGS
4. 修改 `src/verify.c`：重命名 `read()` 为 `read_file()`
5. 编译：`cd src && make`
6. 安装到 Staging：`make install DESTDIR=$TEST_PREFIX/bin MANDIR=... DOCDIR=...`
7. 测试：`make test`
8. 生成 Conan 配方并验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | verify 二进制 SIGSEGV (Signal 11) | `verify.c` 中 `read()` 函数名与 POSIX `read()` 系统调用冲突，musl libc 的 `fread()` 内部调用 `read(fd, buf, count)` 被劫持到用户的 `read(filename, result)`，参数类型不匹配导致段错误 | 将 `read()` 重命名为 `read_file()`，更新两处调用点 |
| 2 | 编译时链接 zlib 失败 | 平台无 zlib 库，Makefile 默认引用 `../zlib` | Makefile 中 USEZ/ZLIB 设为空，禁用 zlib 支持（可选功能） |
| 3 | CC=gcc 找不到编译器 | 平台只有 clang，无 gcc | Makefile 中 CC 改为 clang |
| 4 | SSL 证书验证失败，无法下载源码 | 平台缺少 CA 证书 | 使用 `curl -k` 手动下载，`--no-download` 初始化 |
| 5 | /tmp 只读 | OpenHarmony 文件系统限制 (E002) | 使用 $TMPDIR ($HOME/tmp) |
| 6 | chown 命令不可用 | SELinux 限制 (E046) | Makefile 中 `\|\| true` 处理，非致命 |

## 源码修改

### 补丁 1: 0001-src-Makefile.patch
- 文件: src/Makefile
- 修改: 禁用 zlib（USEZ/ZLIB 清空）、CC=gcc→clang、CFLAGS 调整 (-O3 -fomit-frame-pointer → -fPIC -O2)
- 分类: 平台适配

### 补丁 2: 0002-src-verify.c.patch
- 文件: src/verify.c
- 修改: `read()` → `read_file()`（3处：函数定义 + 2处调用）
- 分类: 平台适配（函数名冲突修复）

## 依赖版本

无编译依赖。zlib 为可选项，已禁用。

## 验证结果

### make test 结果
```
13/13 测试全部通过，退出码 0
```

### Conan 配方验证 (conan-verify)
```
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS
全部 8 道门禁通过
```

### Staging 验证
```
bin/atasm        — 133504 字节, ELF 64-bit ARM64
share/man/man1/atasm.1 — 1803 字节
share/doc/atasm/atasm.txt — 64065 字节
.staging-verified 标记存在
```

## 注意事项

1. atasm 的 Makefile 位于 `src/` 子目录，不在项目根目录
2. 项目无 configure 脚本，构建系统为纯 Makefile，非 autotools
3. `verify` 工具的 `read()` 函数名冲突是关键修复，不修复则所有涉及 MD5 校验的测试都会段错误
4. zlib 支持为可选功能，禁用不影响核心汇编功能
5. NX=disabled 安全警告（L4 门禁），非阻塞，属于平台/编译器限制

---

**编译结束**: 2026-06-29 22:31
**最终状态**: published
