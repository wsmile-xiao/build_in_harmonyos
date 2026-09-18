# DRAFT-8959: musl tmpfile() 硬编码只读 /tmp 恒 EACCES——C 测试框架需代码级 $TMPDIR 替代

## 触发场景

libei 1.5.0 适配（2026-09-15）：munit 测试套全部用例 ERROR
（"unable to create buffer for stderr: Permission denied (13)"），
0 用例实际执行。补丁后 175/176 通过。

## 症状签名

```
test_strstrip   Error: unable to create buffer for stderr: Permission denied (13)
...
No tests run, 0 (100%) skipped.
```

或测试源码内：
```
assertion failed: fp != ((void*)0)
```

## 根因

1. OHOS 沙箱 /tmp 只读（EROFS）——E002 已记录
2. **E002 的盲区**：musl 的 `tmpfile()` 实现硬编码 `/tmp` 前缀（glibc 优先
   读 TMPDIR 环境变量，musl 不读）——设置 TMPDIR **救不了 tmpfile()**
3. munit 在执行每个用例前无条件 `tmpfile()` 捕获 stderr 缓冲（fork 与
   no-fork 模式都走）→ 整套测试 ERROR 而非个别失败
4. 测试源码用 tmpfile() 取临时 fd（测 fd 传递）同样失败

## 修复方案（代码级，语义等价替代）

```c
static FILE *test_tmpfile(void)
{
    static unsigned int seq;
    const char *tmpdir = getenv("TMPDIR");
    char path[512];
    FILE *fp;

    if (tmpdir == NULL || *tmpdir == '\0')
#ifdef P_tmpdir
        tmpdir = P_tmpdir;
#else
        tmpdir = "/tmp";
#endif
    snprintf(path, sizeof(path), "%s/test-tmpf-%ld-%u.tmp",
             tmpdir, (long)getpid(), seq++);
    fp = fopen(path, "w+");
    if (fp == NULL)
        return NULL;
    unlink(path);   /* fd 到 fclose 前持续有效，与 tmpfile 语义一致 */
    return fp;
}
#define tmpfile() test_tmpfile()
```

- 补丁策略：无条件替换（纯 POSIX，无平台宏，R8 合规且跨 musl 系通用）；
  TMPDIR 为空回退 P_tmpdir。**不要用 __OHOS__ 门控**（曾被打回：平台锁死
  + 硬编码路径双违规，AI review High Priority）
- 落点一：测试框架（munit.c 的 stderr_buf 处）
- 落点二：被测代码测试段（`#if _enable_tests_` 内宏替换）

## 兜底方案

- LD_PRELOAD tmpfile shim（E272 DejaGNU 先例）——只救执行期，不救测试
  源码内调用，覆盖不全
- 裁测试（-Dtests=disabled）——丢上游覆盖，不推荐

## 验证

libei 1.5.0：补丁前 0 用例可跑 → 补丁后 utils 35/35、ei 10/10、eis 7/7、
eierpecken 84/85（socket_overflow 为另一平台差异豁免）。

## 适用面

所有 munit 系测试（libinput/libei/libevdev 生态）及任何在测试代码/
框架中调用 tmpfile() 的 C 项目。E002 解决"环境变量层"，本条解决
"musl tmpfile() 函数层"。
