# 包名 `libcob4` 在上游找不到？——它是 libtool `-version-info` 算出来的 ABI 切片；拆库包时"构建范围"必须全量、"安装范围"才能收敛

> DRAFT-libcob4-3.2-libtool-version-info-soname-and-library-only-extraction
> （知识库扩展草稿，路径 B）与 libcob4 3.2 归档同 PR 交付。

任务给的包名是 `libcob4`。在 GnuCOBOL 源码树里 `grep -r libcob4` 一无所获，上游
也没有叫这个名字的仓库 —— 看着像个"无法适配"的任务。实际上 `libcob4` 根本不是
项目名，而是**库自己声明的 ABI 主版本**：

```makefile
# libcob/Makefile.am
libcob_la_LDFLAGS = $(COB_FIX_LIBTOOL) -version-info 6:0:2 -no-undefined
```

libtool 的 `-version-info current:revision:age` 语义：

| 量 | 公式 | 本例（6:0:2） |
|----|------|---------------|
| SONAME | `libNAME.so.(current-age)` | `libcob.so.4` |
| 真实文件名 | `libNAME.so.(current-age).age.revision` | `libcob.so.4.2.0` |

所以 `libcob4` = 「libcob 的 ABI 4 切片」，上游仍是 GnuCOBOL 3.2，与既有的
`archives/g/gnucobol/3.2` **同一份 tarball**（SHA256 `3bb48af4…c2ee2` 逐字相同）。
区别只在交付边界：`gnucobol/3.2` 交付编译器加运行库，`libcob4/3.2` 只交付运行库。

---

## 场景一：包名的推导只看 `current-age`，不看 release/age

`-version-info` 三个数里只有 `current - age` 进 SONAME。`age` 与 `revision` 只影响
文件名和"向后兼容几个版本"的语义。所以：

```bash
grep -nE '_la_LDFLAGS.*-version-info' libcob/Makefile.am
# 6:0:2  →  SONAME libcob.so.4   →  conan name = "libcob4"
#         →  真实文件 libcob.so.4.2.0
```

**判定信号**：任务/下游给出的包名形如 `lib<name><N>`，且

```bash
grep -rnE '_la_LDFLAGS.*-version-info' --include=Makefile.am .
```

有输出 → 包名由 `-version-info C:R:A` 的 `C-A` 决定，**不要**因为搜不到同名上游
仓库就判定任务不可做。

反向信号：工程用 libtool 的 `-release` 而不是 `-version-info`（这时包名里带的是
release 串，不是数字 ABI）；或者 SONAME 由 CMake 的 `VERSION/SOVERSION` 决定
（推导路径不同，见 libharu 那条草稿）。这两种情况下上面这套算法不适用。

顺带一个容易搞混的点：`libcob4` 这种"ABI 数字后缀"包名，和 `libzip` 那种
"项目名就叫 libxxx"的包名长得一样，只能靠**去源码里找 `-version-info`** 区分，
不能靠名字猜。

---

## 场景二：拆库包时，**构建范围**必须保持全量，只有**安装范围**能收敛

拿到"只要 libcob"这个结论后，最自然的动作是：

```bash
./configure ... && make -C libcob        # ← 想省掉编译器的构建时间
```

这在 GnuCOBOL 上会直接砍掉**整个上游测试**。原因不在库，在测试套件的驱动方式：

```bash
$ grep -n 'SUBDIRS' Makefile.am
SUBDIRS = . lib libcob bin cobc config copy po extras doc tests
$ ls tests/testsuite
tests/testsuite            # autotest 生成脚本，用 cobc 编译每个 .cob 用例
```

`tests/testsuite` 是**编译器测试套件**：1226 个用例里绝大多数要先用 `cobc` 把
COBOL 源码编成可执行文件再断言行为。只构建 `libcob/` 子目录 → 没有 `cobc` →
`make check` 跑不起来 → 本包的上游测试数只能写 0，而"上游测试真跑"是硬性口径。

正确的拆法是**把两件事解耦**：

```python
def build(self):
    autotools.configure()
    autotools.make(args=["-j1"])          # 全量：libcob + cobc + cobcrun
    self.run("make MAKEINFO=true -j1 check > <log> 2>&1; ...")   # 上游 1226 用例

def package(self):
    autotools.install(args=["-C", "libcob"])    # 收敛：只装运行库与子目录头
```

于是同一份源码、同一组补丁，既跑了完整上游测试，又只交付运行库。

**判定信号**：

```bash
grep -n 'SUBDIRS' Makefile.am                     # 看看测试目录是否与库目录并列
grep -nE 'testsuite|check_PROGRAMS|TESTS' tests/Makefile.am
```

若测试套件依赖同树里的可执行程序（`cobc`、生成器、代码生成器等），构建就不能
按"我只要哪个目录"来切。

> 反过来的错法同样常见：为了省事直接顶层 `make install` 到包里，然后把不想要的东西
> 删掉。本例顶层 install 会装出 `bin/{cobc,cobcrun,cob-config}`、
> `lib/gnucobol/CBL_OC_DUMP.so`、`share/gnucobol/{config,copy}/**`、
> `lib/libcob.la` —— 用排除法清理不仅容易漏，而且交付清单会随上游版本悄悄变化。

---

## 场景三：伞头文件不在子目录的 install 里

`make -C libcob install` 装的是子目录自己的 `pkginclude_HEADERS`：

```bash
$ grep -nE '^(include_HEADERS|pkginclude_HEADERS)' Makefile.am libcob/Makefile.am
Makefile.am:22:include_HEADERS = libcob.h                                   # ← 顶层！
libcob/Makefile.am:45:pkginclude_HEADERS = common.h version.h cobgetopt.h \
```

而消费者写的是 `#include <libcob.h>`（伞头文件，内容是 `#include "libcob/common.h"`）。
只做子目录 install 的话这个文件**不会**出现在包里，下游直接编不过 —— 但构建本身
不报任何错，只有消费者建到一半才会发现。补法是配方里手工复制：

```python
copy(self, "libcob.h", src=self.source_folder,
     dst=os.path.join(self.package_folder, "include"), keep_path=False)
```

同时别忘了清理 libtool 归档与静态库（`lib/libcob.la`、`lib/libcob.a`）：它们不在
交付物清单里，留着只会让包内容和 `package_type = "library"` 的声明对不上。

**一个有用的自检**：`conan create` 之后直接看包里的目录树。

```bash
$ ls <package_folder>
include  lib                  # 期望：没有 bin/
$ ls <package_folder>/lib
libcob.so  libcob.so.4  libcob.so.4.2.0   # 期望：没有 .la / .a
```

---

## 附带：库把"位置解析结果"缓存在 static 里，测试必须换进程

拆库包时要写消费者测试，这里有个容易踩空的地方：libcob 的临时目录解析结果是
**进程内静态缓存**。

```c
/* libcob/common.c */
static const char *
cob_gettmpdir (void)
{
    static const char *tmpdir = NULL;
    if (tmpdir != NULL) { return tmpdir; }   /* ← 一个进程只解析一次 */
    ...
}
```

所以"把 TMPDIR 换成不可写目录再看行为"这种断言，在**一个进程里只能做一次**：
第二次调用会直接返回第一次的缓存。测试必须写成"每条断言各起一个新进程"，即把
`cob_temp_name()` 的观察放进 shell 驱动（`TMPDIR=... ./test_libcob tmpdir`），
而不是在同一个 C 程序里循环设置环境变量。

顺带，libcob 还会把解析结果**回写**进 `TMPDIR`（`cob_setenv("TMPDIR", tmpdir, 1)`），
供它 fork 出去的外部工具使用 —— 这本身就是一条可观测的断言
（`getenv("TMPDIR")` 必须等于解析结果）。

---

## 复现清单

```bash
# 1) 包名判据（ABI 切片，不是项目名）
grep -nE '_la_LDFLAGS.*-version-info' libcob/Makefile.am      # 6:0:2 → SONAME libcob.so.4
grep -rn 'libcob4' . || echo '上游无此项目名 —— 预期结果，不是"不可适配"'

# 2) 测试驱动判据（决定构建范围能不能收敛）
grep -n 'SUBDIRS' Makefile.am                                  # tests 与 libcob 并列
ls tests/testsuite && grep -c 'cobc' tests/testsuite | head -1  # 套件经编译器驱动

# 3) 头文件层次判据（决定要不要手工补装）
grep -nE '^(include_HEADERS|pkginclude_HEADERS)' Makefile.am libcob/Makefile.am

# 4) 交付物判据（建完直接看树）
conan create archives/l/libcob4/3.2 -pr:h=<ohos> -pr:b=<ohos>
ls <package_folder> && ls <package_folder>/lib
#   期望：只有 include/ 与 lib/libcob.so{,.4,.4.2.0}，没有 bin/、.la、.a

# 5) 上游测试真跑了的证据
grep -aE 'tests behaved as expected|tests were skipped' <build>/libcob4-upstream-check.log
```
