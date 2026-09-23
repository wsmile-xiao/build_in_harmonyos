# DRAFT：已带 `configure` 的 autotools 包在 OHOS 上的最小构建路径（AUX_DIR 定位三元组、半量 E007、别让顶层 make 进 doc/）

> 状态：草稿（待知识库主编 promote）
> 来源：unuran 1.12.0 适配，`archives/u/unuran/1.12.0`
> 类别：autotools / conan / OHOS 三元组 / 构建驱动

## 错误特征

三种表象，看起来互不相干，实际是同一条路径上的三个坎：

1. `configure` 直接退出：

   ```
   configure: error: cannot guess build type; you must specify one
   ```

   而 **E007 的补丁你已经打了**（甚至日志里能看到 `patch` 成功应用）。

2. 换了个包，`configure` 过了，但构建到一半：

   ```
   make[2]: Entering directory '.../doc'
   /bin/sh: makeinfo: not found
   make[2]: *** [Makefile:xxx: unuran.info] Error 127
   ```

3. 打包阶段（或 `make install`）报：

   ```
   mktemp: failed to create directory via template './confXXXXXX': Permission denied
   ```

**关键识别信号**：第 1 条如果伴随"补丁明明打了"，先去看 `configure.ac` / `configure`
里有没有 `AC_CONFIG_AUX_DIR` —— 十有八九 helper 不在源码根。

## 触发条件

一个**已经带 `configure` 和全部 `Makefile.in` 的 autotools tarball**（即发行版
release tarball，不是 git 仓库快照），在 OHOS 上构建时：

1. 它把 `config.guess` / `config.sub` 放在 `AC_CONFIG_AUX_DIR` 指定的子目录
   （`autoconf/`、`config/`、`build-aux/` 都常见），而不是源码根；
2. 它的顶层 `SUBDIRS` 里含一个有额外工具链依赖的目录（`doc/` 要 texinfo、
   `po/` 要 gettext、`tests/` 可能要 valgrind）；
3. 它的 `configure` 由较老的 autoconf 生成，里面有 `umask 077 && mktemp -d`。

## 根因分析

### (1) `AC_CONFIG_AUX_DIR`：helper 不在你以为的地方

`AC_CONFIG_AUX_DIR([autoconf])` 让 autoconf 把 `install-sh`、`missing`、
`config.guess`、`config.sub`、`depcomp` 等辅助脚本装进 `autoconf/`。configure 里
通过 `ac_aux_dir` 变量引用它们；**从源码根找永远找不到**。

而以"改写 `config.guess` 里的三元组"为手段的 E007 补丁，如果写成

```python
path = os.path.join(src_dir, "config.guess")   # ← 只找根
if os.path.isfile(path): ...                    # ← 静默为假，什么都没做
```

就会**无声地失效**：没有报错、没有 warning，只有最终 `configure` 报
"cannot guess build type"。这类"补丁打了但没落地"是最容易浪费一轮 CI 的失败模式。

判据：

```sh
grep -n 'AC_CONFIG_AUX_DIR' configure.ac configure
find <src> -name config.guess -o -name config.sub
```

### (2) E007 常常只需要打一半

同一个 E007，上游 `config.sub` 与 `config.guess` 的 autotools 年份可能不同：

- `config.sub` 往往已经认识 `ohos*` 与 `linux-ohos*`（较新的版本把 `gnu* | android*`
  扩成了 `gnu* | android* | ohos*`，内核列表也加了 `linux-ohos*`）；
- `config.guess` 则**仍然**不认识 `uname -s` = `HarmonyOS` 这个字面量，也没有
  `__OHOS__` 的 libc 分支。

所以正确做法是**每处改写各带自己的 idempotent guard**，而不是"四处一起无条件
插入"。无条件插入会在已经支持 ohos 的 `config.sub` 里制造重复分支，甚至破坏
其语法。

### (3) 顶层 `make` 的 `SUBDIRS` 里有构建期不需要的目录

`SUBDIRS = . scripts src examples experiments tests doc` 这种列表里，`doc/` 只
贡献手册。CI worker 的干净 PATH 没有 texinfo，于是：

- 顶层 `make` → 下到 `doc/` → `makeinfo: not found` → 整个构建失败，
  **尽管库本身早就编好了**；
- 顶层 `make install` 同理。

**不要用命令行覆盖 `SUBDIRS=`**：

```sh
make SUBDIRS="src"          # ← 反模式
```

`SUBDIRS` 是 make 的普通变量，命令行赋值**优先级最高**并且经 `MAKEFLAGS` 传进
每一层 sub-make —— 于是 `src/Makefile` 自己的嵌套 `SUBDIRS`（`utils methods distr
… urng`）也被冲成 `"src"`，install 就漏装子目录里的头文件。

正确做法是 `make -C <dir>` 分目录驱动：

```sh
make -C scripts -j1
make -C src -j1
make -C tests check -j1
make -C src install -j1
```

### (4) `umask 077` + HMDFS（E114）

老 autoconf 生成的 `configure` 会写：

```sh
(umask 077 && mktemp -d ./confXXXXXX)   # ← drwx--S--- on HMDFS
```

HMDFS（OHOS 的分布式文件系统）强制给目录加 setgid 位，`077` 于是产出
`drwx--S---`，**连 owner 都写不进去**。把生成好的 `configure` 里的 `umask 077`
一律换成 `umask 022` 即可（a52dec / adcli / univalue / libxdg 同款做法）。

## 与相邻条目的关系

- **E007（autotools OHOS 三元组）**：本条是它的**定位补充** —— 三元组怎么改是
  E007，改哪儿是本条。凡 `configure.ac` 里有 `AC_CONFIG_AUX_DIR` 的上游都要按本条
  探测。
- **E114（`umask 077` → HMDFS 不可写）**：本条 (4) 是同一件事在"已生成
  configure"场景下的表现。
- **E074（jobserver FIFO）**：同属 OHOS worker 的 make 环境约束，一并带 `-j1`。
- **DRAFT-lazperf-3.4.0-tests-hardcoded-var-tmp-readonly-rootfs**：都涉及只读根
  文件系统，但那条是"测试夹具写死绝对路径"，本条是"configure 自己的临时目录"。

## 修复清单（照抄即可）

```python
_AUX_DIRS = (".", "autoconf", "config", "build-aux", "scripts")

def _find_helper(src_dir, leaf):
    for rel in _AUX_DIRS:
        p = os.path.join(src_dir, leaf) if rel == "." else os.path.join(src_dir, rel, leaf)
        if os.path.isfile(p):
            return p
    return None

def _drop_umask_077(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        data = fh.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(data)

def _patch_ohos_triplet(conanfile, src_dir):
    cg = _find_helper(src_dir, "config.guess")     # ← 不是 src/config.guess
    cs = _find_helper(src_dir, "config.sub")
    # 每一处改写各带 guard（"LIBC=ohos" not in gc 之类），未命中 anchor 时 warning
    # 最后 os.chmod(helper, 0o755)：configure 以 `$SHELL $ac_aux_dir/config.sub` 调用
```

```python
def build(self):
    _patch_ohos_triplet(self, self.source_folder)
    _drop_umask_077(os.path.join(self.source_folder, "configure"))
    autotools = Autotools(self)
    autotools.configure()
    for sub in ("scripts", "src"):          # ← 不去 doc/
        autotools.make(args=["-C", sub, "-j1"])
    autotools.make(target="check", args=["-C", "tests", "-j1"])
```

## 反例（不要做）

| 反例 | 后果 |
|------|------|
| 只在源码根找 `config.guess` | 补丁静默失效，最终以 "cannot guess build type" 失败，白跑一轮 CI |
| 四处 E007 改写无条件插入 | 在已支持 ohos 的 `config.sub` 里插重复分支，可能破坏语法 |
| 顶层 `make` / `make install` | `doc/` 触发 `makeinfo: not found`，整个构建失败 |
| `make SUBDIRS="src"` | 经 MAKEFLAGS 冲掉 `src/` 自己的嵌套 `SUBDIRS`，漏装子目录头文件 |
| 只改 `configure` 忘了 `chmod +x` helper | `cannot run .../config.sub` |
| 重跑 `make check` 时复用旧树来数用例数 | automake 把已有 `.log` 当 up-to-date 跳过，TOTAL 偏低（实测 57 vs 58） |
