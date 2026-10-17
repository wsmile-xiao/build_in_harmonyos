# E999 — OHOS libc 符号族 configure 误检的 ac_cv 禁用模式（fortify __*_chk / fpos64）

## 错误特征

```text
zzat.c:486:26: warning: call to undeclared function '__fread_chk'; ISO C99 and
later do not support implicit function declarations [-Wimplicit-function-declaration]
src/libzzuf/lib-stream.c:577:14: error: use of undeclared identifier 'unknown';
did you mean 'union'?
```

- 症状 1：业务源码调用 `__fread_chk`/`__fgets_chk` 时隐式声明报错（C99 起为错误）
- 症状 2：`FPOS64_CAST(x)` 宏展开为 `unknown`，产生 undeclared identifier 编译错误
- 两者都发生在 configure 已成功通过之后、业务代码编译阶段

## 触发条件

- 构建系统：autotools（configure AC_CHECK_FUNCS / AC_CHECK_TYPES / AC_TRY_COMPILE）
- 阶段：configuration（误检）→ compilation（暴露）
- 平台：HarmonyOS PC（OHOS SDK，musl 派生 libc）
- 场景：项目 configure 检测 glibc fortify `__*_chk` 符号或 fpos64 家族

## 根因分析

OHOS（musl 派生）libc 与 glibc 在这两个符号族上语义不同，而 autoconf 的检测
默认假设 glibc 语义：

1. **fortify `__*_chk`**：OHOS 头文件（fortify/stdio.h）中声明受
   `__FORTIFY_COMPILATION` 门控（需 `_FORTIFY_SOURCE` 才可见）；且
   `__fread_chk` 参数顺序为 `(ptr, size, count, stream, bos)`，与 glibc 的
   `(ptr, ptrlen, size, nmemb, stream)` 不同。configure 的 AC_CHECK_FUNCS
   链接测试因符号真实存在于 libc.so 而误判 HAVE=1 → 业务代码 `#if HAVE___FREAD_CHK`
   分支无声明直接调用 → implicit declaration 错误。
   注意：`__read_chk`/`__recv_chk`/`__recvfrom_chk` 参数序与 glibc 一致且
   libc.so 实际导出，可正常拦截（zzuf 保留后子进程读文件 fuzz 恢复）。

2. **fpos64 家族**：OHOS stdio.h 中 `fpos64_t`/`fseeko64`/`fsetpos64` 分别是
   `fpos_t`/`fseeko`/`fsetpos` 的宏别名，且 `fpos64_t` 是
   `union { char __opaque[16]; long long __lldata; double __align; }`。
   上游 configure 的两种访问探测（`x.__pos` / `(long long)x`）均失败，
   `FPOS64_CAST` 回退为字面量 `unknown` → 编译错误。

## 解决方案

### 推荐方案：ac_cv cache 变量按真实语义选择性禁用/保留

在 configure 命令中注入 autoconf cache 变量（zzuf 配方实现，无需源码补丁）：

```bash
./configure \
  ac_cv_func___fread_chk=no ac_cv_func___fgets_chk=no \
  ac_cv_func_fseeko64=no ac_cv_func_fsetpos64=no \
  ac_cv_type_fpos64_t=no
```

- **禁用**：参数序与 glibc 不一致的 stream fortify（__fread_chk/__fgets_chk）；
  fpos64 家族宏别名（LP64 下 off_t 本为 64 位，与标准接口等价，禁用无损）
- **保留**：参数序一致且实际导出的 fd fortify（__read_chk/__recv_chk/__recvfrom_chk）
  ——保证 LD_PRELOAD 子进程读文件拦截链路可用

### 扩展方案：未知 FILE 布局安全回退（R04，zzuf lib-stream.c）

FILE 结构完全不透明（OHOS `struct _IO_FILE { char __x; }`）时，上游
glibc/FreeBSD/Solaris 快路径的 `get_streambuf_base/pos/count` 返回 NULL/0，
各宏仍按内部缓冲区操作会：对 NULL 地址 `_zz_fuzz`（崩溃）、ungetc 推回字节
被后续读取重复 fuzz（双重翻转）→ 上游测试 MD5 不一致。

补丁要点（patches/0002-src-libzzuf-lib-stream.c.patch）：
- 新增编译期开关 `HAVE_STREAMBUF_LAYOUT`（glibc/FreeBSD/Solaris=1，其余=0），
  宏体内无法嵌套预处理指令 → 受影响宏提供双版本
- 已知布局保留原快路径（`ZZ_FUZZ_STREAMBUF`/`ZZ_FUZZ_STREAM_PRELOAD` 封装）
- 未知布局安全回退：
  - `fread`：仅 fuzz 实际 `ret * size` 字节（跳过已 fuzz 前缀）
  - `getc/fgetc` 及 unlocked：仅 fuzz 成功返回的单字节
  - `fgets/getline/getdelim`：仅 fuzz 公共 API 逐字节返回结果
  - `fseek/fsetpos/rewind`：仅更新逻辑文件位置，不读写内部缓冲区
  - `ungetc`：仅在成功（ret != EOF）时回退逻辑位置，且 `_zz_setfuzzed(fd, 1)`
    标记推回字节已 fuzz，后续读取用 `_zz_getfuzzed` 跳过（避免双重翻转）
- 验证：make check 11/11 全 PASS（check-utils 553/553），组合
  getc/fgetc/unlocked + ungetc + fread MD5 与直接 stdin fuzz 参考一致

### 禁止做法

- ❌ 私造 `__fread_chk` 兼容 shim/stub 猜测 OHOS SDK fortify 语义（E235 同类禁令）
- ❌ 用 `-D_FORTIFY_SOURCE=2` 强行暴露声明（会改变全部调用点参数语义，风险不可控）
- ❌ 未知 FILE 布局下对 NULL streambuf 指针调用 `_zz_fuzz` 或偏移计算
- ❌ 将 check-utils ungetc 类断言作为"平台限制"长期跳过——公共 stdio API
  回退可在当前库配方允许范围内修复（R04 已验证 553/553）

## 验证

```bash
make -j4                                   # 编译全绿
make check                                 # zzuf: 10/11 TESTS，check-utils 522/553 断言通过
./src/zzuf -m -s 7 -r 0.001 cat file-00    # 子进程 md5 == 直接 stdin fuzz md5（拦截恢复）
```

## 关联条目

- 相关: E235（__fd_chk 未导出符号，链接错误）、E414（musl fpos_t 结构）、
  E011（HMDFS umask）、E020（musl FILE opaque）