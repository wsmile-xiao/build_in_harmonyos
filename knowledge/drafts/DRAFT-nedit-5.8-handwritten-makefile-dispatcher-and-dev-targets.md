# 手写 makefile 的"分发器陷阱"：谁在构建末尾执行了刚链接的二进制

> Draft: DRAFT-nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets
> Stem: `nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets
- **严重度**: 2
- **类别**: build-system|makefile|dev-target-boundary|portability
- **触发工具**: make|conan|clang
- **阶段**: build|install

## 错误特征

分发器陷阱的表现形式很反直觉：**编译全部成功之后**才失败。

```
[100%] cd /src/source && make -f Makefile.linux nedit nc
        clang ... -o nedit
        # 到这里一切正常
@source/nedit -V
source/nedit: error while loading shared libraries: libXm.so.4:
        cannot open shared object file: No such file or directory
make: *** [Makefile:xx: linux] Error 127
```

报错是**加载器错误**而不是编译错误，报错点是"运行"，而触发它的那一行藏在
顶层 Makefile 的末尾。如果只扫 makefile 前面的变量定义，很容易完全看不到它。

## 根因分析

NEdit 5.8 的顶层 `Makefile` 是一个 **`.DEFAULT` 分发器**，它的规则体只有三件事：

1. 把 `makefiles/Makefile.<平台>` 符号链接进 `util/`、`Xlt/`、
   `Microline/XmL/`、`source/`；
2. 跑四次子 make；
3. `@source/nedit -V` —— 执行刚刚链接出来的那个二进制。

第 3 步是上游的**冒烟自检**：在"就地编译、系统装了 Motif"的传统源码构建场景
里它是有意义的（新链接的二进制能就地跑起来，说明链接没问题）。但在
`conan create` 里，新链接的 `nedit` 的 `DT_NEEDED` 是 **Conan 缓存**里的
`libXm.so.4`，此时既没有 rpath，也还没有 `LD_LIBRARY_PATH`——加载器找不到它。

值得强调的是：这不是"libXm 没编出来"或"链接参数写错了"。库好好地躺在
Conan 缓存里，只是这一行**太早**执行了它。把这一行去掉，构建立刻变绿。

同一套 makefile 里还并置着另外两类目标，取舍逻辑完全不同：

| 目标 | 类别 | 处置 |
|------|------|------|
| `libNUtil.a` / `libXlt.a` / `libXmL.a` / `nedit` / `nc` | 交付物必需 | 必跑（前三个是静态库，第四个链接它们） |
| `make -C doc man`（生成 `nedit.1` / `nedit-nc.1`） | 交付物需要，但属开发者工具链 | 显式调用，接受 `pod2man` 依赖 |
| `doc` 的 `help` / `faq` / `html` 目标 | 纯开发者专用 | 不跑：需要 perl 的 setext 与 XSLT 处理器 |
| `check` / `test` / `ctest` | **上游不存在** | 不跑，也不发明；manifest 如实写 0 |

`doc/Makefile` 自己的第一行说明把边界划得很清楚：

```
instructions:
	@ echo "This make file is intended for NEdit developers only."
```

上游顶层构建也刻意不含 `docs`：源码根 Makefile 的注释写着 *"users may not have
Perl installed"*，所以手册页与帮助文本的再生成被留给开发者。**上游已经把
"默认交付"和"开发者专用"分好了，移植者要做的是沿用这个分界，而不是把所有
目标一网打尽。**

## 解决方案

**主方案**: drive-sub-makes-directly-and-classify-every-target

### (a) 判定"真构建"还是"分发器"，然后只复刻前半段

读一遍顶层 Makefile。如果是分发器，就复刻它的**第一步**（把平台 makefile 放进
四个子目录），然后按依赖顺序**直接驱动子 make**：

```python
_SUBDIRS = (
    ("util", "libNUtil.a"),          # 被 nedit/nc 链接
    ("Xlt", "libXlt.a"),             # 被 nedit 链接
    ("Microline/XmL", "libXmL.a"),   # 被 nedit 链接
    ("source", "nedit nc"),          # 链接上面三个静态库
)
```

复刻时用**拷贝**而不是符号链接。上游用 `ln -s`，但符号链接在 Windows 检出的
仓库与 HMDFS 上语义都不友好（权限、大小写、清理），拷贝在语义上完全等价。

### (b) 用命令行覆盖上游变量，不改上游文件

`makefiles/Makefile.linux` 里全是 `=` 赋值：

```make
CC=cc
AR=ar
CFLAGS=-O -I/usr/X11R6/include -DUSE_DIRENT -DUSE_LPR_PRINT_CMD -ansi -U__STRICT_ANSI__
ARFLAGS=-urs
LIBS=-L/usr/X11R6/lib -lXm -lXt -lX11 -lm
```

`make` 的**命令行赋值优先级高于文件内赋值**（这是 POSIX make 的规则，也是
GNU make 的规则）。所以 `make -f Makefile.linux CC=... AR=... CFLAGS=... LIBS=...`
可以一次性解决三件事：替换掉上游写死的 `cc`/`ar`、去掉 `/usr/X11R6` 路径、
注入 Conan 依赖的 `-I`/`-L`/`-l`。**不需要任何上游补丁。**

### (c) 给每个目标分类，再决定跑不跑

- **交付物必需** → 必跑，且给明确 target（不要依赖默认目标）。
- **交付物需要但属开发者工具链** → 显式调用，并在 notes.md 里写明它带来的
  额外工具依赖（本包：`make -C doc man VERSION="NEdit 5.8"` 需要 `pod2man`，
  产物是 `nedit.1` / `nedit-nc.1`）。
- **纯开发者专用** → 不跑，并在 notes.md 里记录原因（需要 perl/XSLT）。
- **上游不存在** → 不跑、不发明。manifest 里如实写
  `upstream_tests.exists: false` / `test_count: 0`。

## 验证

```sh
# 分发器陷阱的静态自证：确认顶层最后一行的存在与位置
grep -n '@source/' Makefile
# 目标清单（确认没有 check/test）
grep -n '^[a-zA-Z_.]*:' Makefile source/Makefile.common
# 子 make 驱动顺序：前三个必须先于 source/
CI_PACKAGES="archives/n/nedit/5.8" zsh ci/conan/build_and_test.sh
```

构建日志里应当**只出现四次子 make**，且**不出现**任何执行 `source/nedit` 的行。

## 关联条目

- 前置本仓库条目 `DRAFT-unuran-1.12.0-configure-auxdir-triplet-patch-and-doc-subdir-make`：
  那条讲 autotools 项目"别让顶层 make 进 doc/"，本条讲手写 makefile 项目
  "顶层 make 会在末尾执行自己的产物"——两者都是**顶层目标不等于交付物**。
- 后续条目 `DRAFT-nedit-5.8-headless-smoke-test-for-motif-x11-apps`：既然构建期
  不能执行产物，验证只能搬到 `test_package`，并且需要为"没有 X server"设计
  测试路径。
