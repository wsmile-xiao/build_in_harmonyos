# DRAFT: musl/OHOS argp API 缺失补齐模式（argp-standalone）

> 草稿编号：DRAFT-argp-musl-gap-bridge（待审核 promote）
> 来源：argp-standalone 1.4.1（ericonr fork）适配，2026-09-04
> 路径 B（知识库扩展）素材

## 问题

OHOS 使用 musl libc。argp(3)（`argp.h` + `argp_parse`/`argp_usage`/`argp_help`）
是 **glibc 专属**的命令行解析 API，musl 从未提供：

```console
$ ls /path/to/ohos/sysroot/usr/include/argp.h
ls: cannot access ... No such file or directory
```

大量 GNU 软件（coreutils 系、elfutils、gnulib 生态）源码里
`#include <argp.h>`，在 musl/OHOS 上：

- 编译期：`fatal error: 'argp.h' file not found`
- 链接期（自带 argp.h 副本时）：`undefined reference to 'argp_parse'`

## 模式：argp-standalone 补齐库

argp-standalone 把 glibc 的 argp 抽成独立静态库（`libargp.a` + `argp.h`），
是 Alpine Linux 等 musl 生态的标准解法。与 musl-fts / musl-obstack 同属
"glibc 有、musl 无"补齐库家族。

### 下游怎么消费（conan 配方写法）

```python
def requirements(self):
    # host 依赖（self.requires）而非 tool_requires：
    # argp 是目标机运行时 API，参与目标机链接，随制品链分发
    self.requires("argp-standalone/1.4.1")
```

仓库内实证：`archives/e/elfutils/0.195/conanfile.py`、
`archives/e/execstack/20130503/conanfile.py`。

### argp-standalone 包本身的适配四要点

1. **autoreconf 自举**：GitHub archive tarball 不含 configure（autoreconf
   产物不进版本库）。设备/CI 无系统 automake 时
   `tool_requires("automake/1.18") + tool_requires("libtool/2.5.4")`。
2. **libintl.h 空壳**：OHOS musl 的 libintl.h 宏在、函数符号不在。
   configure 传 `ac_cv_header_libintl_h=no` → argp-help.c 走
   `#define dgettext(d,m) (m)` 直通分支。
   - 勿用 `-Wno-int-conversion` 糊（链接期照样缺 `__dcgettext`）
   - 勿 `LIBS=-lintl`（引入 gettext 重依赖；NLS 已禁不需要）
3. **noinst 设计**：上游 Makefile.am 全是 `noinst_*`（设计为被内嵌编译），
   `make install` 空操作 → package() 手工装 `argp.h` + `libargp.a`
   （Alpine APKBUILD 同法）。
4. **HMDFS umask**：configure/config.status 内嵌 `umask 077 && mktemp -d`，
   HMDFS 上建出的临时目录缺组执行位不可写（E011）→ autoreconf 之后
   替换 `umask 077` → `umask 022`。

### C++ 下游测试注意

test_package 的 C++ 探针建议 `-static-libstdc++`（OHOS 上
`libc++_shared.so` 搜索路径不可靠：动态链 C++ 运行时的探针报
`Error relocating ./test_probe: _ZdlPv: symbol not found`）。

## 验证证据（2026-09-04 实测）

- 上游测试（make check）：ex1-test + permute-test，**2/2 = 100%**
- conan create + test_package（argp_parse 解析往返 8 断言）：**8/8 = 100%**
- conan-verify G0-G4 + L2/L4/L5：全 PASS

## 推广面

任何用 argp 的 GNU 软件适配到 OHOS 都可复用此模式：
elfutils（已实证）、execstack（已实证）、addrwatch 系（系统装路径）、
以及未来的 coreutils 系工具。
