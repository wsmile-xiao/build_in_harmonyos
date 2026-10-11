# DRAFT 知识条目（md 成对版）— 手写 Makefile 的"变量槽位"改造法：新增 $(SLOT) 而非覆盖变量，并用指纹验证补丁真的生效

> Status: DRAFT | 来源: tetraproc/0.9.2 真机 shadow CI 2026-10-04（r2 第 5、6 轮）

## 使用说明

适配"手写 Makefile"类上游（Fons Adriaensen 系列、大量老 CLI/GUI 项目）时，
需要从外部注入 `-I`/`-L`/编译器/平台差异参数。**不要命令行整体覆盖
`CPPFLAGS`/`LDLIBS`**（会冲掉上游自己的 `-DVERSION`、`-DSHARED`、target-specific
`+=` 追加），正确做法是给 Makefile 打补丁新增**专用槽位变量**。本条同时给出
两个高危伴生坑与指纹化自检。

## 适用范围

- 任何 `CPPFLAGS +=` / `LDLIBS +=`（含 target-specific `+=`）的手写 Makefile。
- 交叉编译（OHOS）需要注入 profile 工具链、依赖 include/lib 路径的场景。

## 输入 / 输出

- 输入：上游 Makefile（确认哪些变量被 `+=` 追加、哪些值来自 `$(shell pkg-config ...)`）。
- 输出：补丁新增的槽位（如 `PCONFCFL`/`FREETYPE_CFLAGS`/`SYSLIBS`/`CONAN_LDLIBS`，
  配 `?=` 默认值）+ 配方命令行传参；以及两条"补丁是否生效"的指纹检查。

## 模式

```make
# 补丁新增（保留上游所有原有行不动）:
PCONFCFL ?=
FREETYPE_CFLAGS ?=
SYSLIBS ?= -lrt
CPPFLAGS += ... -DVERSION=\"$(VERSION)\" $(PCONFCFL)        # 原行追加槽位
tetraproc: LDLIBS += -lsndfile ... $(SYSLIBS) $(CONAN_LDLIBS)  # 原链接行尾部加槽位
```

```python
# 配方侧（R33：编译器来自 profile conf）:
self.run('make -C "{src}" -j1 CXX="{cxx}" PCONFCFL="{i}" FREETYPE_CFLAGS="{f}" '
         'SYSLIBS="{s}" CONAN_LDLIBS="{L}"'.format(...))
```

要点：
1. `?=` 给默认值（SYSLIBS 默认 `-lrt`，OHOS 传空），Linux/OHOS 一份 Makefile 两用。
2. 槽位必须**写进使用点**（编译行/链接行）——见伴生坑 A。
3. target-specific `LDLIBS +=` 与命令行槽位变量互不干扰（槽位经 `$(...)` 引用展开）。

## 伴生坑 A：重新生成补丁时丢槽位 token（本次真实踩中）

补丁迭代（如把 replace_in_file 方案改写为 .patch 文件）时极易漏抄某个槽位：
本次 `$(CONAN_LDLIBS)` 在重生成时丢失 → make 命令行参数**确实传了**，但链接行
不再引用它 → 所有 `-L` 路径消失 → `ld.lld: error: unable to find library
-lsndfile/-lfftw3f/-ljack/...` 全体报错。

指纹：`grep -m1 'make -C' 日志` 确认命令行参数在，再看链接命令行里 `-L` 是否
为空——"参数在、效果无"＝Makefile 引用点丢了，不是配方传参错。

## 伴生坑 B：补丁未生效的统一指纹检查

补丁结构错（如 conandata patches 嵌套，见姊妹条目）时 build 跑的是未打补丁
源码。每次跑 runner 前/后 grep 编译命令行：

```sh
grep -m1 'clang' <run>/logs/stdout.log | grep -c -- '-march=native'   # 应为 0
grep -c 'pkg-config' <run>/logs/stdout.log                            # 应为 0（已替换）
```

## 示例（本次实证）

- 丢槽位：链接行 `...-lX11  `（尾部空），8 个库全部 unable to find（r2 第 5 轮）。
- 补回 `$(CONAN_LDLIBS)` 后：链接行带全部 `-L`，两个可执行文件链接成功（第 6 轮）。

## 查重边界

- `pcaputils-0.8-handwritten-makefile-linkvar-override`：讲"链接变量名不是
  LDFLAGS→反推真实变量名后命令行覆盖"，是**改名**场景；本条是**新增槽位**场景
  （覆盖会冲掉上游 target-specific `+=` 与自注入宏）。
- `DRAFT-simh-3.8.1-makefile-cc-full-command-override`（未提交）：CC 全命令覆盖。
- `fasttext-0.9.2-cmake-hardcoded-march-native-strip`：CMake 场景去 `-march=native`。
- `zerofree-1.1.1-makefile-linkline-flags-and-musl-transitive-include`：musl 链接旗标。
  均未覆盖"槽位注入 + 丢 token 指纹"模式。
