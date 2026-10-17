# 只读 `/tmp` 平台上的“代码级”临时文件：`tmpfile()` / 硬编码 `/tmp` 的适配

- **条目**：`knowledge/drafts/DRAFT-code-level-tmpfile-readonly-tmp.kv`
- **来源软件**：tboot 1.10.5（`lcptools-v2/lcp2_mlehash`，手写 Makefile + zlib/OpenSSL）
- **日期**：2026-09-24
- **触发**：本地 `make`/`conan create` 后运行工具，功能静默失效（工具返回 0 但没有结果）
- **关联**：**E002**（`/tmp` 只读 → 设置 `TMPDIR`，环境变量层）——本条是其**代码层**补充

## 错误签名

```
creating a temporary file to uncompress ... : failed!     # 上游自带的 LOG 文本（tboot）
$ touch /tmp/xx
touch: '/tmp/xx': Read-only file system                   # 平台事实（E002）
```

注意：很多包的这类失败**不会**让进程以非 0 退出（上游只 `goto error` 后 return false，
调用方忽略返回值），因此 CI 的“退出码”门禁抓不到它，只有功能级测试（真实跑一次工具并断言输出）才能发现。

## 根因

1. `tmpfile()` 由 libc 实现，固定使用 **`P_tmpdir`**（OHOS/glibc/musl 默认均为 `/tmp`），
   **不读 `TMPDIR` 环境变量**；
2. OHOS 的 `/tmp` 是**只读挂载**（erofs，E002），`tmpfile()` 必然返回 `NULL`；
3. 上游代码的解压/缓存/原子写路径随之走错误分支，**功能整体不可用**；
4. E002 的修法（`TMPDIR=$HOME/tmp`）只影响 configure/make 等**构建脚本**自己的临时文件，
   对包内 C/C++ 代码里的 `tmpfile()` 与硬编码 `"/tmp"` **无效**。

## 推荐方案（source-patch，行为等价）

把 `tmpfile()` 换成“在 `$TMPDIR` 下 `mkstemp()` + `unlink()` 的匿名流”；`$TMPDIR`
未设置时回落 `/tmp`（与原行为完全一致，不会改变 x86/glibc 环境表现）：

```c
static FILE *open_scratch_stream(void)
{
    const char *tmpdir = getenv("TMPDIR");
    char path[1024];
    int fd;

    if ( tmpdir == NULL || *tmpdir == '\0' )
        tmpdir = "/tmp";
    if ( snprintf(path, sizeof(path), "%s/<tool>-XXXXXX", tmpdir) >= (int)sizeof(path) )
        return NULL;
    fd = mkstemp(path);
    if ( fd == -1 )
        return NULL;
    if ( unlink(path) != 0 ) {      /* 立即 unlink：保持 tmpfile() 的匿名语义 */
        close(fd);
        return NULL;
    }
    return fdopen(fd, "w+b");
}
```

要点：
- **保留匿名语义**：`mkstemp` 后立刻 `unlink`，进程退出/崩溃不会留下垃圾文件（与 `tmpfile()` 一致）；
- **不要**改成在源码树/当前目录建临时文件（会污染构建目录，且并发构建互相踩）；
- 若上游是硬编码 `"/tmp/xxx"`（而非 `tmpfile()`），同样替换为 `"$TMPDIR/xxx"` 形式；
- 头文件：需要 `<stdlib.h>`（`getenv`/`mkstemp`），`<unistd.h>`（`unlink`/`close`），`<stdio.h>`（`snprintf`/`fdopen`）。

## 验证方法（可复用探针）

```bash
# ① 复现失败（对照）：TMPDIR 指向只读 /tmp
TMPDIR=/tmp     <tool> <args> 2>&1 | grep -i "temporary file"   # 期望 failed
# ② 修复生效：TMPDIR 指向可写目录
TMPDIR=$(pwd)   <tool> <args> 2>&1 | grep -i "temporary file"   # 期望 succeeded
# ③ 证明代码确实在用 $TMPDIR（而不是碰巧走了别的路径）
TMPDIR=$(pwd)/does-not-exist <tool> <args> 2>&1 | grep -i "temporary file"  # 期望 failed
```

③ 是关键：只做 ①②**不能**证明修复生效（可能仍固定用别处），③ 把“临时文件确实创建在 `$TMPDIR`”钉死。

## 现网证据（tboot 1.10.5 实测）

| 项 | 值 |
|---|---|
| 上游代码 | `lcptools-v2/mlehash.c:300` `fdecompressed = tmpfile();`（gzopen 解压 MLE 镜像时使用） |
| 复现 | `TMPDIR=/tmp lcp2_mlehash --create --alg sha256 --verbose image.bin` → `creating a temporary file to uncompress ... : failed!`；`touch /tmp/xx` → `Read-only file system` |
| 修复 | `archives/t/tboot/1.10.5/patches/0004-lcptools-v2-mlehash.c.patch`（+29/-1） |
| 回归 | `archives/t/tboot/1.10.5/test_package/test.sh` 的 **OH-1/OH-2** 断言（②③ 两条探针，`conan create` 每轮实跑） |

## 适用边界

- 适用于**任意**在 C/C++ 代码里用 `tmpfile()` 或硬编码 `/tmp` 的包（含构建期工具与运行期工具）；
- 不适用于纯 shell/CMake 脚本层的临时文件（那属于 E002 的环境变量修法）；
- 若上游新版本已改成 `mkstemp`/`TMPDIR`，本条目不再适用（可随 KB 演进收敛）。
