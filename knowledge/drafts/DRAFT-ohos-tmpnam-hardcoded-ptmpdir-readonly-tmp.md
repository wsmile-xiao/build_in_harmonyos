# DRAFT-ohos-tmpnam-hardcoded-ptmpdir-readonly-tmp — libc `tmpnam()` 落只读 `/tmp` 且无视 TMPDIR/TEMP

## 错误特征

上游测试用 `tmpnam()`/`tmpfile()` 建临时文件，在 OHOS 真机上**打开必失败**。两种
形态（RetroArch 1.22.2 实测）：

```
# 形态 1：shell 直接写 /tmp
zsh: read-only file system: /tmp/rahello.c

# 形态 2：测试断言挂（根因被断言掩盖）
66%: Checks: 3, Failures: 1, Errors: 0
libretro-common/test/hash/test_hash.c:48:F:Core:test_sha1:0:
  Assertion 'fd != ((void*)0)' failed        ← tmpnam 给的 /tmp/... fopen 失败

# 形态 3：测试框架自身的临时通信文件
.../check_msg.c:317: Unable to create temporary file for communication;
  may not have permissions to do so             ← libcheck 也想写 /tmp
```

## 触发条件

- 平台：OHOS（根文件系统只读，`/tmp` 不可写）。
- 阶段：**testing / runtime**（跑上游测试、框架建通信管道时）。
- 代码模式：`tmpnam(buf); fopen(buf, "wb")`、`tmpfile()`、任何写死 `/tmp/...` 的
  scratch 路径。

## 根因分析：两层叠加 + 一个致命误解

1. **OHOS `/tmp` 只读**（只读根文件系统，`HMDFS`/rootfs 挂载策略）。
2. **libc `tmpnam()` 锚定编译期常量 `P_tmpdir=/tmp`**，按 POSIX 只保证返回
   「可用路径名」；实现**不读 `TMPDIR`/`TEMP`** —— 这点与 glibc 一致，但 glibc
   环境 `/tmp` 可写所以从不暴露。

**致命误解**：以为「设了 `TMPDIR` 就行」。真机探针（OHOS aarch64）：

```c
#include <stdio.h>
#include <stdlib.h>
int main(void){
  char b[512]; tmpnam(b);
  printf("tmpnam=%s P_tmpdir=%s TMPDIR=%s\n", b, P_tmpdir, getenv("TMPDIR"));
  return 0;
}
```

```
$ TMPDIR=$PWD/tmp TEMP=$PWD/tmp ./probe
tmpnam=/tmp/tmpnam_Mfcpen P_tmpdir=/tmp TMPDIR=/storage/.../tmp
```

无论 `TMPDIR`/`TEMP` 指哪，`tmpnam()` 恒返回 `/tmp/...`。

**关键区分（框架行为 ≠ libc 行为）**：libcheck 的 `open_tmp_file()` 自己实现了
探测链 **`TEMP` → `P_tmpdir` → `TMPDIR`**（mkstemp 分支）。所以：
- 框架（libcheck）要临时文件 → **`export TEMP=<可写目录>` 即可**（TEMP 优先于
  P_tmpdir）；
- 测试代码直接调 libc `tmpnam()` → 改代码，环境变量救不了。

## 修复方案

**测试代码：显式探测环境构造 scratch 路径**（仅测试侧可移植性改动）：

```c
#include <unistd.h>   /* getpid */
...
const char *tmpdir = getenv("TEMP");
if (!tmpdir || !*tmpdir) tmpdir = getenv("TMPDIR");
if (!tmpdir || !*tmpdir) tmpdir = ".";
snprintf(tmpfile, sizeof(tmpfile), "%s/lrc_test_%d.tmp", tmpdir, (int)getpid());
fd = fopen(tmpfile, "wb");
```

**配方/运行环境**：对框架的 mkstemp 探测链，`export TEMP` + `TMPDIR` 指向可写
构建目录（Conan 的 `self.run('TEMP=... TMPDIR=... <test>')`）。

实证：RetroArch 1.22.2 补丁 0005（test_hash/test_utils 改造）+ conanfile build()
内 `TEMP/TMPDIR`，5 套件 3+89+16+16+3 = **127/127**。

## 禁止做法

| 禁止 | 原因 |
|------|------|
| 只设 `TMPDIR` 指望修 `tmpnam()` | 实测 `tmpnam()` 不读环境变量，恒 `/tmp` |
| chmod / remount `/tmp` | 只读根文件系统，不可写也不应绕 |
| scratch 写死源码目录 / `$HOME` | CI 源码目录可能只读；HOME 受 HMDFS 权限族影响；`TEMP`/`TMPDIR` 探测 + `.` 回退才最小可移植 |

## 边界（与既有条目的区别）

- **E215** 是 **Lua/LuaRocks 族**（`os.tmpname` + 可重定位打包）；本条是 **C libc
  族**（测试代码直接调 `tmpnam()/tmpfile()`），语言层、修复位置都不同。
- **DRAFT-sexpp gtest-TMPDIR** 是 gtest 捕获流族（框架内部路径）；本条覆盖
  「测试代码直接用 libc」与「libcheck 类 mkstemp 探测链」两个新面。
- E011（umask/HMDFS）是权限位族；本条是**挂载只读**+libc 常量锚定，root 也无解。

## 验证

```sh
echo x > /tmp/probe                     # read-only file system（复现层 1）
TMPDIR=$PWD/tmp ./probe                 # tmpnam=/tmp/...（复现层 2：无视环境）
TEMP=$PWD/tmp ./lc-tests/test_hash      # 框架链：3 checks, 0 failures（修复生效）
```
