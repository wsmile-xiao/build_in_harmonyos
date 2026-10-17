# DRAFT: GitHub tag 归档 autotools 自举与 triplet 钉扎——conan conf 钉同值 host/build triplet 过 config.guess 且保 cross_compiling=no

- **草稿 ID**: DRAFT-E652-parasail-2.6.2-conan-autoreconf-triplet-pin
- **来源库**: parasail 2.6.2（SIMD 序列比对库，C，OHOS PC aarch64, clang 15.0.4, HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 问题（三层，真机实测）

parasail 上游只发 GitHub tag 归档
（`https://github.com/jeffdaily/parasail/archive/refs/tags/v2.6.2.tar.gz`），
归档内**没有生成的 configure**，只有 `configure.ac + Makefile.am + m4/`。
在鸿蒙设备上用 Conan 配方构建时，`conan create` 的第一轮在 configure 期
即死，报错尾部：

```text
checking build system type...
build-aux/config.guess: line 1613: /storage/.../ws/tmp/cgfiBFJb/dummy.c: Permission denied
build-aux/config.guess: unable to guess system type
This script (version 2024-07-27), has failed to recognize the
operating system you are using.
UNAME_SYSTEM  = "HarmonyOS"
configure: error: cannot guess build type; you must specify one
```

1. **归档层（无 configure）**：GitHub tag 归档不是 `make dist` 产物，
   autotools 生成物全部缺失 ⇒ `build()` 必须先 `autoreconf -fi` 自举；
   而 CI worker PATH 没有 automake/libtoolize（`/data/service/hnp/bin`
   只有 autoconf 家族），设备 harmonybrew 的 automake 也不进 worker PATH
   ——「设备全绿 ≠ CI 绿」的经典假绿源。
2. **平台识别层（config.guess 失败）**：`config.guess` 对
   `uname -s = HarmonyOS` 没有任何识别分支（2024-07-27 最新版实测仍失败）。
   且它并不是「升级版本就能救」：`config.guess` 内部要在 `$TMPDIR` 下写
   `dummy.c` 并编译探测，HMDFS 目录模式位丢失使写文件先行
   `Permission denied`（E490 同族）——探针路径死掉，识别分支再全也走不到。
3. **conan 侧（不传 triplet）**：conan 2.29 的 `AutotoolsToolchain` 对
   os=OHOS 目标**不会自动传 `--host/--build`**（实测 configure 直接走
   config.guess），于是 configure 第一阶段就 `cannot guess build type`。

附带一坑：parasail 的 `AC_INIT` 用
`m4_esyscmd([./version.sh])` 提版本——**autoreconf 期**就会执行
`version.sh`，要求构建 PATH 内有 `egrep/awk/tr`（OHOS 的
`/data/service/hnp/bin` 与 `/system/bin` 均提供；GNU autoconf 调 `egrep`
打 obsolescent 警告，无害）。

## 方案（推荐路径：conf 钉同值 triplet）

配方 `generate()` 里**在构造 `AutotoolsToolchain` 之前**：

```python
self.conf.define("tools.gnu:host_triplet", "aarch64-linux-ohos")
self.conf.define("tools.gnu:build_triplet", "aarch64-linux-ohos")
```

`AutotoolsToolchain` 读这两个 conf 后会显式传 `--host/--build`
（跳过 config.guess，也就跳过了它的 HMDFS 探针）；`config.sub`
2024-07-27 版已接受 `aarch64-linux-ohos`（规范化为
`aarch64-unknown-linux-ohos`，可用
`./build-aux/config.sub aarch64-linux-ohos` 自证）。

**关键点是两个值必须相同**：host == build ⇒ autoconf 判
`cross_compiling=no`，因此

- `AC_RUN_IFELSE` 运行期探测照常真跑（不会像 E007 警告的那样
  「误判交叉 ⇒ 跳运行探测 ⇒ 生成错 config.h」）；
- 上游 Makefile.am 里 `if CROSS_COMPILING ... else TESTS += ...`
  形态的测试面保留——parasail 的 `make check` 就挂在 else 分支下，
  host/build 不同值时 `make check` 会**静默一个用例都不跑**。

自举前置（同配方内完成闭环）：

```python
def build_requirements(self):
    self.tool_requires("automake/1.18")   # aclocal/automake
    self.tool_requires("libtool/2.5.4")   # libtoolize + libtool.m4 (LT_INIT)

def generate(self):
    VirtualBuildEnv(self).generate()      # 把工具 bin 与 ACLOCAL_PATH 注入 PATH

def build(self):
    if not os.path.isfile(os.path.join(self.source_folder, "configure")):
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
```

`LT_INIT` 需要的 `libtool.m4` 由 `libtoolize` 复制进 `m4/`
（日志可见 `libtoolize: copying file 'm4/libtool.m4'`）。

## 修复后实测（同轮 create 日志）

```text
checking for ARM NEON support... default
checking whether C compiler accepts -fopenmp-simd... yes
checking for OpenMP flag of C compiler... -fopenmp
config.status: creating Makefile
```

## 与既有条目的关系

- E007 记录了同一失败签名与 patch-autotools-ohos.pl 补丁方案，并警告
  「用 --build/--host 绕过 ⇒ 误判交叉编译 ⇒ AC_RUN_IFELSE 全跳过、
  config.h 错误」——本条目给出**不触生成物、且不落交叉误判**的第三条路：
  conf 钉**同值** triplet；并把「TESTS 挂在 CROSS_COMPILING 条件下会被
  静默清空」这一假绿面显式化。
- E490 记录了 autotools 辅助脚本权限位丢失面；本条目的 config.guess
  探针 `dummy.c: Permission denied` 是其在 HMDFS 上的具体表现之一。

## 复现命令（设备可直接执行）

```sh
sh build-aux/config.guess                 # 期望：unable to guess system type
sh build-aux/config.sub aarch64-linux-ohos  # 期望：aarch64-unknown-linux-ohos
```
