# DRAFT-7C3E：libbsd 假依赖要核到符号级，且共享库链接探针会骗人（metastore 1.1.2）

- **触发实例**：metastore 1.1.2 适配（2026-10-02，积分赛任务，Agent 7C3E）
- **错误签名**：`fatal error: 'bsd/string.h' file not found` / `undefined symbol: strmode` / `-lbsd` 找不到
- **类别**：ohos / libc / build / link / portability
- **严重度**：1（不处理则本包完全无法编译）

## 症状

未打补丁时，`make` 的第一个目标就死：

```
        CC      obj/metaentry.o
./src/metaentry.c:39:11: fatal error: 'bsd/string.h' file not found
# include <bsd/string.h>
```

台账侧同时给出两条「需要整个 libbsd」的信号：README 的 `Requirements: … libbsd`，
以及 Makefile 里按 `uname -s` 在非 BSD 平台追加的 `metastore_DLIBS += -lbsd`。
制品仓侧也确实没有：`conan download "libbsd/*" -r=ohpcd --only-recipe` → `Found 0 pkg/version recipes`。

## 根因一：台账说「一个库」，符号级说「一个符号」

| 层次 | 结论 |
|---|---|
| 全树 grep `strmode` | **仅 1 处命中** `src/metaentry.c:656`（`mentries_dump()` 渲染 `--dump` 的 mode 列），且树内**无任何定义** ⇒ 纯外部导入 |
| 其余 string 系调用 | 全是 ISO C：memset / strcmp / strerror / strlen / strchr / strncmp / strcat / snprintf / strrchr / strdup / memcpy / strftime / bcmp（`bcmp` 单独链接探针 rc=0，musl 原生） |
| `-lbsd` 名义上伺候的 strlcpy / strlcat | `nm -D` OHOS libc.so 实测**均为 `T`**（地址同为 `0x11d80`）—— musl 原生导出，**根本不是 libbsd 依赖** |
| `strmode` | `nm -D` 查无此符号；`<bsd/string.h>` 头文件也不存在 ⇒ **双重不可得** |

⇒ 真实依赖面 = **1 个符号**。为一个格式化函数去适配发布整个兼容库不经济。
既有工艺里的正解是**树内 shim**（rdate 1.11 的 `adjtime`→`adjtimex`、OpenSSH 的 `openbsd-compat/strmode.c` 同属一手法）。

## 根因二：`-shared` 探针把「不存在」误判成「存在」（本次实测踩中）

首次判断符号存在性时用了共享库链接探针：

```bash
$CC -target aarch64-linux-ohos -shared -fPIC probe.c -o probe.so   # 永远成功
```

得到 `strmode / strlcpy / reallocarray / strtonum` **全部 RESOLVES** 的结论。
**根因：动态库链接默认允许未定义符号**——探针根本没去 libc 里找符号，ld 自然不报错。

改为链接**可执行文件**（必须解析全部符号）后真相立刻浮现：

```
[UNDEFINED] strmode        -> undefined symbol: strmode
[UNDEFINED] reallocarray   -> undefined symbol: reallocarray
[UNDEFINED] strtonum       -> undefined symbol: strtonum
[UNDEFINED] explicit_bzero -> undefined symbol: explicit_bzero
[UNDEFINED] setprogname    -> undefined symbol: setprogname
[RESOLVES]  strlcpy  strlcat  arc4random  getopt_long  listxattr  bcmp
```

若当时据「musl 有 strmode、libbsd 是纯假依赖、什么都不用改」推进，产出的就是一个**必然红 CI** 的 PR。

## 修复

补丁 `archives/m/metastore/1.1.2/patches/0001-strmode-shim-drop-libbsd.patch`（3 个 hunk / 2 个文件 / 3896 B）：

1. **树内 `strmode(3)`**，守卫用 `#ifndef HAVE_STRMODE`——沿用 OpenSSH `openbsd-compat/strmode.c` 的惯例，
   **不是** `__OHOS__` 平台宏（R8：前者允许、后者被 PF5 硬闸拦）。真实 libc 若自带则 `-DHAVE_STRMODE` 选系统的。
2. **逐字节对齐 BSD 语义**：类型位 `-/d/l/c/b/s/p/?`、九个权限位、setuid(`S`/`s`)/setgid(`S`/`s`)/sticky(`T`/`t`) 双字形。
3. **缓冲尺寸严丝合缝**（最容易写错的一处）：BSD strmode 写 10 字符（1 类型 + 9 权限）+ 1 字符 ACL 占位符 + 1 字符 NUL
   = **12 字节**，而调用方是 `char mode[11 + 1]` = 12 字节，**恰好等大，无溢出**。
   若误省掉 ACL 占位符只写 11 字符 + NUL，`--dump` 列宽会与上游不一致。
4. **同步摘掉 `-lbsd`**（连同三层 `ifeq BSD / ifneq DragonFly / ifneq Darwin`），原地留注释。
   摘完已无任何符号需要它——**一个符号都不丢**。

## 测试必须证明 shim 正确，而不只是「能跑」

libbsd 被替换掉的就是 `strmode`，所以只测「二进制能启动」完全不足以证明替换正确。
消费者测试（`test_metastore.sh`）用两条**鸿蒙特有**断言钉死它：

- 让 `--dump` 的 mode 列与 **`ls -ld` 逐条对拍**（一个完全独立的实现），
  覆盖 `-`/`d`/`l`/`p` 四种文件类型 + setuid / setgid / sticky 分支，共 10 条；
- 额外硬编码断言四个字形：`-rwsr-xr-x`、`-rwSr--r--`、`drwxr-sr-x`、`drwxrwxrwt`。
  任一分支写错都会红。

## 适用边界

- 适用于任何在 OHOS/musl 上把 libbsd 当 requirement 的包，尤其只用到少数几个 BSD 便利函数的 C99 工具。
  同族已验证两例：rdate 1.11、metastore 1.1.2。
- 只有当真实依赖面确实是**大量** BSD 符号时，才值得按 R36 先适配并发布 libbsd 到制品仓。
  rdate 1.11 的 notes 明确记录过该判断：「libbsd 未发布 ⇒ 卸除假依赖是唯一正解」。

## 关联

- 配方补丁：`archives/m/metastore/1.1.2/patches/0001-strmode-shim-drop-libbsd.patch`
- 配方：`archives/m/metastore/1.1.2/conanfile.py`（R33：CC 从 Conan conf 读，不裸用 `${CC}`）
- 消费者测试：`archives/m/metastore/1.1.2/test_package/test_metastore.sh`（9 组 / 12 条断言）
- 适配账本：`archives/m/metastore/1.1.2/notes.md`
