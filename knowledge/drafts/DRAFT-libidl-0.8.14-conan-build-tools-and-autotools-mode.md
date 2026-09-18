# OHOS 上构建期工具包的三个坑 + autotools 交叉/原生抉择

> 知识草稿（与 libidl 0.8.14 归档适配 PR 一同交付）。
> 来源：libidl 0.8.14 适配，`conan create`（ohos-aarch64 profile, clang 15）rc=0，
> 上游 `tstidl` 1/1（真机）、`test_package` 消费者断言 14/14 真机通过。
> 载体：libIDL 需要 bison+flex（tarball 只带 `parser.y`/`lexer.l`）与 glib（`PKG_CHECK_MODULES`）。

## 一、bison 工具包：数据目录前缀失真 + 硬编码 m4 路径

### 现象

把 bison 作为 `tool_requires` 拉入后，`make` 只给出：

```
  GEN    stamp-parser
make: *** [Makefile:1279: stamp-parser] Error 1
```

没有任何 bison 报错——**因为上游 Makefile 的 `YFLAGS = -d -v 2>/dev/null` 把 bison 的
stderr 丢进了 /dev/null**。手动复现才能看到真实错误：

```sh
$ BISON_PKGDATADIR=<bison-pkg>/share/bison <bison-pkg>/bin/bison -y -d -v parser.y
bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory   # ①
$ BISON_PKGDATADIR=… <bison-pkg>/bin/bison -y -d -v parser.y                     # 修①后
bison: m4 subprocess failed                                                       # ②
make: *** [stamp-parser] Broken pipe                                              # ②的另一种表现
```

### 根因

1. **数据目录 `/=前缀`**。制品仓的 bison 是经 autotools + Conan（`--prefix=/` + `DESTDIR`）
   打包的，二进制按 `/share/bison` 找 `m4sugar.m4`，而文件实际在
   `<bison-pkg>/share/bison`。
2. **硬编码 m4 路径**。二进制里记录的 m4 程序是**发布机上的绝对路径**：

   ```sh
   $ strings <bison-pkg>/bin/bison | grep -E '^/[a-z/]*m4$'
   /data/service/hnp/bin/m4
   ```

   该路径在设备上不存在 → bison 通过 m4 管道生成代码时失败（写管道即 EPIPE，所以
   还可能表现为 `Broken pipe` 而不是清晰的 "m4 not found"）。

### 修复（`generate()` 注入环境变量）

```python
bison = self.dependencies.build["bison"]
env = Environment()
env.define("BISON_PKGDATADIR", os.path.join(bison.package_folder, "share", "bison"))
m4 = shutil.which("m4")          # 设备上 autoconf 依赖的 m4，一定存在
if m4:
    env.define("M4", m4)         # 覆盖硬编码路径
env.vars(self).save_script("conanbuildenv-bison")
VirtualBuildEnv(self).generate() # tool_requires 的 bin 注入 PATH（否则 configure 找不到 flex/bison）
```

> 排查口诀：**bison 类错误先去掉 `2>/dev/null` 看 stderr；`BISON_PKGDATADIR` 治“找不到
> m4sugar.m4”，`M4` 治“m4 subprocess failed / Broken pipe”。**

## 二、flex 版本：`flex/2.6.4` 的包不含可执行文件

`tool_requires("flex/2.6.4")` 后 configure 报：

```
checking for flex... no
checking for lex... no
configure: error: flex is required to create the libIDL scanner
```

检查包内容可知 **`flex/2.6.4` 的包没有 `bin/`**（只有库/头等），而 `flex/2.6.4.2` 提供
`bin/flex`（2.6.4 版本）。改成 `self.tool_requires("flex/2.6.4.2")` 后 configure 正常：

```
checking for flex... flex
checking for bison... bison -y
checking for bison... yes
```

## 三、autotools 模式：AC_RUN_IFELSE 要“非交叉”，config.guess 又必须绕开

libIDL 的 `configure` 里有 `AC_RUN_IFELSE`（检测 `guint64` 的 printf/scanf 格式）。

- 传不同的 `--build`/`--host`（仓库里最常见的写法
  `--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos`）会让 autoconf 认为
  在交叉编译，直接失败：

  ```
  checking for format to printf and scanf a guint64... configure: error:
  cannot run test program while cross compiling
  ```

- 完全不传三元组则会执行 `config.guess`，而现代 `config.guess`（2025-07-10）在
  OHOS 上**自己就会失败**（HMDFS 上无法创建临时文件）：

  ```
  config.guess: can't create /…/cgcKHPjm/dummy.c: Permission denied
  config.guess: unable to guess system type
  ```

**结论：`--build` 与 `--host` 取同一个 OHOS 三元组**（如
`aarch64-linux-ohos`，仓库中 aalib 等 28 个配方也是这么写的）：

```python
tc.configure_args += ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
```

这样 autoconf 用显式三元组（不跑 config.guess），`cross_compiling=no`，`AC_RUN_IFELSE`
编译出的 aarch64 程序在设备上原生执行：

```
checking for format to printf and scanf a guint64... %llu
```

## 四、依赖包 `.la` 的前缀失真：libtool 链接中断

链接本库时出现：

```
libtool: link: warning: library `…/pcre2…/lib/libpcre2-8.la' was moved.
libtool: link: `//lib/libpcre2-8.la' is not a valid libtool archive
make[2]: *** [Makefile:450: libIDL-2.la] Error 1
```

glib/pcre2/libffi 的包内 `.la` 记录了 `libdir='/lib'`（与自身 `.pc` 同源的
`--prefix=/` + `DESTDIR` 失真）。Conan 链路不需要 `.la`，构建前删除依赖包的 `lib/*.la`
即可（与已合入的 `archives/b/bookloupe/2.0` 同法）：

```python
for name in ("glib", "pcre2", "libffi"):
    dep = self.dependencies.get(name)
    for la in glob.glob(os.path.join(getattr(dep, "package_folder", "") or "", "lib", "*.la")):
        os.remove(la)
```

## 五、公开头文件依赖必须显式传播（Conan 2）

`IDL.h` 公开 `#include <glib.h>`，但 test_package 编译报
`fatal error: 'glib.h' file not found` —— Conan 2 的 `self.requires()` **默认不把依赖
暴露给消费者**。修法（仓库惯例，见 aravis/atk）：

```python
self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
self.cpp_info.requires = ["glib::glib"]     # glib 无组件时用包级 target
```

## 验证

```sh
conan create archives/l/libidl/0.8.14 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# rc=0；上游 ./tstidl sample.idl（真机）exit 0；test_package 14/14 断言
```

## 相关

- E011（HMDFS 上 `umask 077` 临时目录不可写）与本条同属 HMDFS 语义族；
- “Conan `--prefix=/` + `DESTDIR` 导致 `.pc`/`.la` 前缀失真”与本条第三节(四)同源，
  可交叉引用；
- `archives/b/bookloupe/2.0`（删除依赖 `.la`）为已合入先例。

## 附：不要在上游 PR 中携带 `config.sub`/`config.guess` 全文

同一个仓库的 libart-lgpl 2.3.21 PR 最初把 OHOS 感知的 `config.sub`（2364 行）与
`config.guess`（1818 行）作为文件放入 `patches/`，结果平台 AI 检视直接**跳过**：

```
⚠️ 本次变更过大（7 个可审文件、4513 行，预估需 4 轮分片审查），已超出 AI 代码评审的
处理范围，本次跳过。建议拆分为更小的 PR 以获得有效评审。
```

AI 检视跳过 = 评审门禁拿不到“无 P0/P1”的结论。正确做法是**最小补丁**：给上游自带的
`config.sub` 加一个 16 行的早退分支（见 `archives/a/a52dec/0.7.4`）：

```sh
+# aarch64 and HarmonyOS were introduced after this bundled config.sub.
+case $1 in
+  aarch64-*-linux* | aarch64-*-ohos* | aarch64-linux-ohos)
+    echo "$1"
+    exit 0
+    ;;
+esac
```

配合显式 `--build`/`--host`（不执行 `config.guess`），效果与替换整个脚本相同，而 PR
的可审规模下降了 99%。
