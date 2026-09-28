# DRAFT-freetype-2.14.3.2.1-hmdfs-script-exec：HMDFS 用户存储禁止直接 exec shebang 脚本，configure/libtool 须经解释器调用

> Contributor: LIMInGZE666 | Status: Draft | Updated: 2026-09-26
> Source: freetype 2.14.3.2.1 适配 HarmonyOS PC（真机 ohos 原生 conan create 实证）
> 对应：`knowledge/drafts/DRAFT-freetype-2.14.3.2.1-hmdfs-script-exec.kv`

## 现象

真机（HarmonyOS PC）跑 `conan create`，autotools 工程在 configure 阶段即失败：

```console
/system/bin/sh: /storage/Users/currentUser/.conan2/p/b/freete4863f215cf42/b/configure: Permission denied
ERROR: freetype/2.14.3.2.1: Error in build() method
ConanException: Error 126 while executing
```

三个反直觉的实测事实（决策矩阵，均为真机实验）：

1. 文件模式 `-rwxrwx---`，owner 正确，**照样被拒**——与 x 位无关；
2. 把脚本 `cp` 到 `~/tmp` 再直接 exec，**同样被拒**——与所在目录无关；
3. `sh ~/.conan2/…/b/configure --version` **正常执行**（输出 "Copying modules.cfg"）——
   解释器显式调用可行；ELF 二进制的 exec 完全正常。

## 根因

HMDFS（HarmonyOS 用户存储，`/storage/Users/currentUser`）在语义层禁止对
shebang 脚本的**直接 exec**（一律 EACCES），`chmod` 加 x 位也不生效
（与 E046 同宗）。可执行文件必须满足「ELF 二进制」或「经显式解释器调用」
二选一。

对 autotools 工程而言，直接 exec 脚本的调用点有整条链：

| exec 点 | 位置 | 后果 |
|---|---|---|
| 顶层 `configure` | conan `autotools.configure()` 直接 exec | Error 126，构建直接死 |
| 内层 `builds/unix/configure` | `builds/unix/detect.mk` 两条 make 配方 | `make setup unix` 时 EACCES |
| `libtool`（编译/链接/安装全程） | `builds/unix/unix-cc.in` 的 `LIBTOOL := …/libtool` + `install.mk` | 每个编译/链接动作 EACCES |
| `install-sh` | `AC_PROG_INSTALL` 在 PATH 找不到 ELF install 时的回退 | 安装阶段 EACCES |

安全面（无需改）：`config.guess`/`config.sub`/`config.status` 上游本身就是
经 `$SHELL` 调用的（autoconf 生成代码：`ac_config_guess="$SHELL
${ac_aux_dir}config.guess"`、`$SHELL $CONFIG_STATUS`）。

## 方案（按 exec 点分层，全部可移植——CI/Linux 上同样合法）

**① 配方层：`sh` 显式调用顶层 configure（替代 `autotools.configure()`）**

```python
# conanfile.py build()
cfg = os.path.join(self.source_folder, "configure")
args = ["--prefix=/"]   # ⚠️ 必须是 /：conan 的 autotools.install() 以
                        # DESTDIR=<package_folder> 执行 make install，
                        # prefix 传 package_folder 会导致路径翻倍嵌套
args += ["'--bindir=${prefix}/bin'", "'--sbindir=${prefix}/bin'",
         "'--libdir=${prefix}/lib'", "'--includedir=${prefix}/include'",
         "'--oldincludedir=${prefix}/include'"]
args += ["--enable-shared", "--disable-static"]     # 或 static 组合
args += ["--with-zlib=no", …]                       # 与原 configure_args 一致
self.run("sh '{}' {}".format(cfg, " ".join(args)), env="conanbuild")
```

参数集与 conan `Autotools.configure()` 默认完全一致（可直接从首次失败
RUN 行抄）。

**② 构建系统层：make 配方里的脚本调用改 `$(SHELL)` 前缀**

```makefile
# builds/unix/detect.mk（两条分支都改）
        $(SHELL) $(TOP_DIR)/builds/unix/configure $(value CFG)
        $(SHELL) ./configure $(value CFG)
# builds/unix/unix-cc.in
LIBTOOL := $(SHELL) $(FT_LIBTOOL_DIR)/libtool
```

`$(SHELL) $(top_builddir)/libtool` 本就是 libtool 官方 aclocal 的标准形式
（`LIBTOOL='$(SHELL) $(top_builddir)/libtool'`），是上游模板自己偏离了标准。
注意连带修 `unix-def.in` DISTCLEAN 列表里的 `$(LIBTOOL)` → 裸路径
（否则 `rm $(SHELL) …` 会把 `/bin/sh` 当文件删——危险）。

**③ install 工具层：PATH 注入 toybox install（ELF），零补丁**

```python
# conanfile.py generate()（os == "OHOS" 分支）
env.append_path("PATH", "/system/bin")   # /system/bin/install = toybox ELF
```

`AC_PROG_INSTALL` 在 PATH 找到 ELF install 即 `INSTALL=<path> -c`，
不再回退 `install-sh` 脚本。真机验证 `/system/bin/install` 前 4 字节
为 `7f 45 4c 46`（ELF 魔数）。

## 验证（真实证据）

freetype 2.14.3.2.1 真机（HarmonyOS PC aarch64，ohos 原生构建）：

- 修复前：`configure: Permission denied` / Error 126（顶层 configure exec 点）；
- 修复后：`conan create . --build=missing -pr:h ~/.conan2/profiles/ohos-aarch64`
  全流程通过，日志可见 `/bin/sh …/libtool --mode=compile clang …` 正常回显；
- 消费者探针 **18/18 全绿**：FT_Init → 版本一致（2.14.3 == 编译期宏）→
  内存加载嵌入 TTF → 字形映射 → Load/Render 光栅化出墨 → issue-1063 等价
  码位循环 → 资源释放；
- 包结构核对：`include/freetype2/ft2build.h`、`lib/libfreetype.so{,.6,.6.20.6}`、
  `lib/pkgconfig/freetype2.pc` 落位正确（无路径翻倍）。

## 适用边界

- **触发面**：HMDFS 用户存储上原生构建 + 构建链直接 exec shebang 脚本
  （autotools 工程最典型：configure/libtool/install-sh 三件套）；
- **反例**：CI（Linux worker）不受影响——但 `$(SHELL)` 前缀方案在 Linux
  上同样合法，可放心写进配方/补丁，无需平台分支；
- **反例**：纯 CMake/meson 工程的 cmake/ninja 调用链无此问题（全是 ELF）；
- **反例**：报错发生在非 `/storage/Users/currentUser` 路径 → 先查别的权限问题。

## 关系

- 同宗：E046（HMDFS chmod 不生效）——HMDFS 语义层拒绝文件系统操作的另一面；
- 姊妹问题：`DRAFT-freetype-2.14.3.2.1-prefix-destdir-double-path`
  （--prefix 与 DESTDIR 叠加路径翻倍，同为真机首轮失败修复）。

## 查重

按 `HMDFS` / `Permission denied` / `Error 126` / `shebang` / `libtool` /
`解释器` 检索 `knowledge/graph/` 与 `knowledge/drafts/`：

- 既有条目多为特定签名（E007 config.guess、E011 TMPDIR、E046 chmod），
  无「HMDFS 脚本直接 exec 被拒」的机理条目；
- E046 与本条同宗但对象不同（权限位写入 vs 脚本 exec），不合并，
  以 similar_to 关联。
