# 发行版为什么能省掉那个宏？——glibc 的兼容垫片不是目标平台的性质

> Draft: DRAFT-nedit-5.8-use-dirent-musl-vs-distro-cflags
> Stem: `nedit-5.8-use-dirent-musl-vs-distro-cflags` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-nedit-5.8-use-dirent-musl-vs-distro-cflags
- **严重度**: 3
- **类别**: portability|musl|glibc|distro-patching|libc
- **触发工具**: clang|make|conan
- **阶段**: compilation

## 错误特征

```
util/printUtils.c:63:10: fatal error: 'sys/dir.h' file not found
   63 | #include <sys/dir.h>
      |          ^~~~~~~~~~~
```

稳定、干净、不需要看第二遍的错误——但前提是你没在做相反的事。危险的方向是
**反过来**：因为 Debian 的 `debian/rules` 里没有 `-DUSE_DIRENT`，就认为这个宏
可有可无，于是把它从 OHOS 配方里也去掉。这时报错才出现，而且报错点
（`<sys/dir.h>`）与真正的起因（CFLAGS 抄错了）隔了好几层。

## 根因分析

`util/printUtils.c` 用一个宏在两种目录 API 之间切换：

```c
#ifdef USE_DIRENT
#include <dirent.h>
#else
#include <sys/dir.h>
#endif /* USE_DIRENT */
```

`<sys/dir.h>` 是 1980 年代 BSD 的接口。**glibc 至今保留它**——它只是
`<dirent.h>` 的一个兼容垫片，里面是 `struct dirent` 的别名与几个老函数声明：

```c
/* glibc's sys/dir.h is a thin compatibility shim over dirent.h */
#include <dirent.h>
```

于是 Debian 的构建可以做一件在 OHOS 上做不到的事：**把 CFLAGS 整个覆盖掉**。

```make
# debian/rules
CFLAGS = -DBUILD_UNTESTED_NEDIT -DHAVE__XMVERSIONSTRING \
	-Wall $(shell dpkg-buildflags --get CFLAGS)
...
$(MAKE) CFLAGS="$(CFLAGS)" linux
```

`-DUSE_DIRENT` 和 `-DUSE_LPR_PRINT_CMD` 一起被丢掉了，编辑器照样编得过——
因为 glibc 还认得 `<sys/dir.h>`。

**这里的关键转念：发行版能省掉一个宏，往往是该发行版 libc 的性质，而不是上游
或目标平台的性质。** 把发行版的补丁与 CFLAGS 当作"上游实测基线"照抄，就正好把
"只对 glibc 成立"的假设带到了 musl 上。musl 不提供 `<sys/dir.h>`，`#else`
分支直接失败。

### 两类宏，两种处置

必须区分清楚：

| 类别 | 例子 | 处置 |
|------|------|------|
| 上游 makefile 里已有的平台默认宏 | `makefiles/Makefile.linux` 的 `-DUSE_DIRENT`、`-DUSE_LPR_PRINT_CMD` | **保留**。它们是"上游为本平台实测选择"的配置。 |
| 发行版额外加的宏 | Debian 的 `-DBUILD_UNTESTED_NEDIT`、`-DHAVE__XMVERSIONSTRING` | **单独评估**。这是该发行版的取舍，在 OHOS 上是否必要需要证据（本项目结论：都不需要）。 |

第一类是"上游说该平台需要它"；第二类是"某个发行版决定加上它"。混为一谈，
就会在该留的地方删掉、在该删的地方留下。

## 解决方案

**主方案**: treat-distro-cflags-as-libc-specific-and-audit-each-define

```python
cflags = list(tc.cflags)
cflags += [f"-D{d}" for d in tc.defines]
cflags += [f"-I{d}" for d in incdirs]
# 上游 Linux 平台 makefile 里的两个宏，原样保留：
cflags += ["-DUSE_DIRENT", "-DUSE_LPR_PRINT_CMD"]
# 不抄 Debian 的 -DBUILD_UNTESTED_NEDIT / -DHAVE__XMVERSIONSTRING
```

顺带两个相关的取舍：

- **不要用 `-ansi` 压低语言标准。** 上游 `makefiles/Makefile.linux` 写的是
  `-ansi -U__STRICT_ANSI__`（2006 年的历史遗留）。Debian 换成了
  `-std=gnu17`。OHOS 上沿用后者：现代 clang 下 `-ansi` 会与系统头里的扩展
  声明冲突，产生大量与移植无关的报错。
- **不要给 libc 同名头文件放垫片作为第一选择。** 万一某个包必须走
  `#else` 分支（宏名不可改、或代码依赖 `struct direct` 的布局），可以带一个
  `files/sys/dir.h` 并用 `-I` 排到系统头之前。但那会往包里塞一个与 libc 同名的
  头文件，成员类型宽度可能与 `struct dirent` 不一致，且随 libc 升级漂移。
  **上游已有宏开关时，打开开关永远更干净。**

### 审查动作

1. 看发行版 `debian/rules` 的 `CFLAGS`/`CPPFLAGS`/`LDFLAGS`，以及
   `debian/patches/series`；
2. 对每一条问："它是在绕开哪个 libc / 哪个版本的具体行为？"
3. 凡是涉及 libc 头文件、feature macro（`_GNU_SOURCE`/`_DEFAULT_SOURCE`）、
   语言标准版本的条目，一律在目标平台 sysroot 上单独验证
   （例如 `ls <sysroot>/usr/include/sys/dir.h`）。

## 验证

```sh
# 确认宏开关与两个分支确实存在
grep -n '#ifdef USE_DIRENT' -A4 util/printUtils.c
# 确认上游平台 makefile 里本来就有这个宏（"保留"是有依据的）
grep -n 'USE_DIRENT' makefiles/Makefile.linux
# 确认 Debian 把它丢掉了（这就是"发行版性质"的证据）
grep -n 'USE_DIRENT' debian/rules
# 目标平台 sysroot 上确实没有这个头文件
ls <sysroot>/usr/include/sys/dir.h    # 期望：No such file

CI_PACKAGES="archives/n/nedit/5.8" zsh ci/conan/build_and_test.sh
```

## 关联条目

- 相近条目 `DRAFT-openvi-7.9.33-nonautotools-argv0-mode-musl-pty-ncurses-override`：
  同属"老代码在 musl 上的 libc 差异"这一类，那条是 terminfo/PTY 语义，本条是
  头文件可用性。
- 同批条目 `DRAFT-nedit-5.8-generated-source-and-private-motif-symbol`：
  那条讲"不定义某个宏"是本包的正解，本条讲"必须定义某个宏"——两者都是
  "宏该不该定义"的判断，判据分别是"目标平台缺什么"与"要不要私有 ABI。
