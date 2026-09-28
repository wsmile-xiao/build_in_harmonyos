# E543 — 上游 tarball 自带 ltmain.sh 与 aclocal.m4 声明的 libtool 版本错配

## 错误特征

典型日志（libydpdict 1.0.4 实测，OHOS aarch64 + clang 15）：

```
../libtool[1249]: func_opt_split: inaccessible or not found
libtool: Version mismatch error.  This is libtool 2.2.6b Debian-2.2.6b-2ubuntu1,
but the definition of this LT_INIT comes from libtool 2.4.
libtool: link: (cd .libs && ...)   ← 链接期第一次调用 libtool 即失败
```

注意 **configure 阶段通常是通过的**（自检路径不触发这些内建函数），错误要等到
`make` 第一次执行 `libtool --mode=compile/--mode=link` 才出现。因此容易被误判为
"编译器/工具链问题"，实际与编译器无关。

ksh（`/bin/sh` = MIRBSD KSH）报 `inaccessible or not found`，bash 报 `command not found`，
两者都要覆盖进 error_signature。

## 触发条件

- 构建系统: autotools（configure + libtool，`Makefile.am` 用 `lib_LTLIBRARIES`）
- 阶段: linking（`make` 第一次调用 libtool）
- 源码形态: **发行 tarball**（自带 `configure`/`Makefile.in`/`aclocal.m4`/`ltmain.sh`），
  且其中 `ltmain.sh` 与 `aclocal.m4` **不同源**
- 交叉构建环境: CI worker 无系统 `libtoolize`，无法自动重建 ltmain.sh

## 根因分析

libtool 的产物由两部分输入拼装：

| 输入 | 提供什么 | libydpdict 1.0.4 实测值 |
|---|---|---|
| `aclocal.m4`（内联 LT_INIT 定义） | libtool 主脚本的骨架版本 | libtool **2.4**，`macro_revision=1.3293` |
| `ltmain.sh` | libtool 的**内建 shell 函数**（func_dirname/func_basename/func_stripname/func_opt_split/func_append 等） | 自称 libtool **2.2.6b**，`package_revision=1.3017` |

`configure` 生成 `libtool` 时以 aclocal.m4 的 LT_INIT 定义为准，而函数体只在
ltmain.sh 里。**降级的 ltmain.sh 不提供 2.4 版主脚本需要的 9 个核心函数**，于是
生成出来的 `libtool` 只要一被调用就报函数不存在；同时主脚本内部版本校验也会打印
`Version mismatch error`。

本项目核对过程（排除法，避免误判）：解包字节数逐项核对（`ltmain.sh` = 243469 字节，
与 tarball 内一致），确认**不是下载/解包损坏**，而是上游发行件本身错配；
用 GNU libtool 2.4 官方发行包的 `ltmain.sh`（282745 字节，`package_revision=1.3293`）
覆盖后，`configure` / `make` / `make install` 全部 rc=0。

## 解决方案

### 推荐方案

**用与 aclocal.m4 声明版本同号的 GNU libtool 官方发行包 ltmain.sh 覆盖残缺件。**

`conandata.yml` 增加一个构建期下载项（官方源 + sha256，满足 R39）：

```yaml
libtool_source:
  url: https://ftpmirror.gnu.org/libtool/libtool-2.4.tar.gz
  sha256: 13df57ab63a94e196c5d6e95d64e53262834fe780d5e82c28f177f9f71ddf62e
```

`conanfile.py` 的 `source()` 在解包上游源码后覆盖：

```python
def source(self):
    get(self, **self.conan_data["sources"][self.version], strip_root=True)
    self._replace_ltmain()

def _replace_ltmain(self):
    libtool_source = self.conan_data["libtool_source"]
    get(self, **libtool_source, destination="libtool-release", strip_root=True)
    shutil.copyfile(
        os.path.join(self.source_folder, "libtool-release", "libltdl", "config", "ltmain.sh"),
        os.path.join(self.source_folder, "ltmain.sh"),
    )
```

要点：

1. **版本号必须对齐 aclocal.m4**，不是"越新越好"——用 2.4 是因为该 tarball 的
   aclocal.m4 声明 2.4（`macro_revision=1.3293`）。
2. 覆盖必须发生在 `configure` 之前（`source()` 里做，`build()` 只用生成的 libtool）。
3. sha256 与文件名需与 `conandata.yml` 一致，CI 的源码身份校验以 (文件名, sha256) 为准。

### 回退方案

无法判定应取哪个 libtool 版本时，用 `tool_requires` 补 autotools 工具链后重新生成：

```python
def build_requirements(self):
    self.tool_requires("libtool/2.5.4")
    self.tool_requires("automake/1.18")
    self.tool_requires("autoconf/2.72")
```

再 `autoreconf -fi`（libtoolize 会按 aclocal.m4 重建 ltmain.sh）。
注意：会重新生成 `configure`，若配方已给 `configure` 打补丁（config.guess/config.sub）
需按 E011 核对补丁是否被冲掉。

### 禁止做法

- ❌ 用 `ACLOCAL=/bin/true AUTOMAKE=/bin/true AUTOCONF=/bin/true AUTOHEADER=/bin/true`
  压掉 maintainer 规则（E041 手法）：**不修复函数缺失**，链接期照样失败。
- ❌ 手工往 ltmain.sh 里补写缺失的 `func_*` 函数：函数间相互调用，人工补写必然残缺，
  且升级上游版本后失效。
- ❌ 判定为"clang/ld 工具链不支持"而直接 `env_unsupported` 上报：与本模式无关，
  换官方 ltmain.sh 即可通过。

## 验证

```bash
# 1. 诊断（版本是否同源）
grep -m1 'package_revision=' $SRC/ltmain.sh
grep -m1 'macro_revision='   $SRC/aclocal.m4
head -3 $SRC/ltmain.sh              # VERSION=2.x
grep -m1 '# libtool (GNU libtool)' $SRC/aclocal.m4

# 2. 修复后：make 期间 libtool 不再报 func_*
conan create <recipe> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
grep -c 'func_.*: \(inaccessible\|command\)' reports/conan-create.log   # 期望 0
```

## 关联条目

- `E551`（CONFIG_SHELL=bash 与老 ltmain.sh 的转义问题）——同样定位在 ltmain.sh 质量，
  但根因是 shell 选型导致的转义丢失，与本条的"版本错配/函数缺失"不同。
- `E041`（bypass-autotools）——在**其它**模式（configure 被 maintainer 规则重生成）下可用；
  在本模式下无效（见"禁止做法"）。
- `DRAFT-E2187`（dist-hook 删掉 autotools 辅助文件）——上游发行缺陷的另一支：那条是
  **文件整体缺失**导致 configure 跑不起来，本条是**文件存在但版本错配**导致链接期失败。
- `DRAFT-6487`（HMDFS 下 CONFIG_SHELL 内联 /bin/sh）——同一批 autotools 交叉构建坑，
  解法手段（命令前缀赋值 SHELL=/bin/sh）可复用，但触发机制不同。
