# KB-ATBOOT notes — 老旧 autotools 包引导缺陷一站式修复

## 原理

2008~2015 年代上游发布的 autotools 源码包在 OHOS aarch64（HMDFS + musl + 无 automake）
上有一类**引导层**共性缺陷。它们与库源码逻辑无关，全部发生在 configure/make 尚未
真正编译任何 C 代码之前，因此可以机械检测、机械修复：

### A 类：tarball 缺 config.guess / config.sub

老 automake（≤1.10 时代）打包惯例是不把 config.guess/config.sub 放进 tarball
（`AC_CANONICAL_TARGET` 的 aux 目录留空），期望打包者在 autoreconf 时补齐。
现代 Linux 上 `autoreconf -fi` 会自动注入，但鸿蒙 PC 设备没有 automake/aclocal，
于是 configure 在 `$ac_aux_dir/config.guess` 处直接失败：

```
configure: error: cannot guess build type
    You must specify one using the `--build' and `--host' action flags.
```

**修复**：注入官方 autoconf 归档脚本（`vendor/config.guess`+`config.sub`，
随本 SKILL 入仓，非 fork），chmod 755。脚本版本 2018 年代，其 `aarch64-*-linux-*`
判定分支对 `aarch64-linux-ohos` triplet 返回正确结果（已实测）。

### B 类：config.status 内嵌 umask 077（HMDFS 权限坑）

老 autoconf 生成的 config.status 用 `umask 077 && mktemp -d ./confXXXXXX` 创建
临时目录。在 HMDFS 文件系统上 chmod/权限语义被忽略（E046），700 权限的临时目录
**创建者自己也无法写入**，config.status 在写 `subs-1.sed`/`out`/`config.h` 时
"Permission denied" 半途而废——但 configure 仍返回 rc=0（假成功），真实症状是
**Makefile/config.h 全部缺失**，make 一跑 `No targets specified` 才暴露。

**修复**：`sed -i 's/umask 077/umask 022/g' configure`。与 commoncpp2 1.8.1 的
0002 补丁、io_lib 1.14.9 的 0002 补丁完全同源（三库实证）。

### B' 类：maintainer-mode mtime 倒挂（E248 扩展）

`Makefile.in: Makefile.am`、`configure: configure.ac` 是 GNU make 的内建依赖规则。
tarball 解包或 conan patch 应用后，若生成者（.am）mtime 晚于被生成者（.in），
make 判定 .in 过期，调用 `missing automake-1.16` 重生成——设备无 automake，exit 127。

**修复**：`touch -r Makefile.am Makefile.in`（及 configure:configure.ac 对），
与知识图谱 E248 的 `os.utime` 处方等价，本 SKILL 以 shell 形式一并覆盖。

## 为什么是"知识库拓展"而不是"单个库补丁"

- 三类特征在 **≥3 个互不相关的库**上独立实证：srf 0.1（A+B）、io_lib 1.14.9（B+B'）、
  commoncpp2 1.8.1（B）
- 检测逻辑是**纯机械特征**（文件存在性 + mtime 比较 + 日志正则），无任何库专属逻辑
- 修复动作是**配方无关的 shell 片段**，可直接内联进任何 conanfile.py
- 受影响库群体明确：2008~2015 年代、autotools、上游停更的老库（这正是积分赛库源
  的主要构成），后续命中率高

## 边界（明确不适用）

1. **只管引导层**。configure 之后的编译/链接失败（musl API 缺失、C++ ABI、
   线程栈大小等）是另一类问题，查知识图谱相应条目
2. **vendor 脚本版本上限**。2018 config.guess 对更老的 configure（AC_CANONICAL_SYSTEM
   旧宏、2005 前）可能接口不匹配；此时按 E007/E160 手工 patch
3. **umask 只处理 077**。其他值未实证，不做无证据扩展
4. **与 E248 的关系**：E248 是 mtime 倒挂的配方级 os.utime 处方（已入正式库）；
   本 SKILL 把它并入 shell 流水线并扩展 A 类检测。配方若已用 E248 方案，勿重复
5. **不适用于 cmake/meson 包**（无 config.guess 概念）
6. **--build/--host 禁令不解除**：R15 家族禁止用交叉 flag 绕过 config.guess，
   本 SKILL 是"补齐脚本让 configure 自己猜对"，与禁令方向一致

## 复现与验证记录

- `reproduce.sh --sample <srf src>`：phase1 `reproduced`（rc=0 假成功 +
  Makefile 三件全缺失）/ phase2 `fixed`（Makefile 三件全生成）——2026-10-01 本机实测
- 检测退出码矩阵：健康 0 / 缺脚本 1 / 倒挂 2 / 双命中 3
- SIGPIPE 防护：全程日志重定向文件，无管道接 head

## 对 conan 配方作者的集成建议（srf 样例配方即模板）

```python
def build(self):
    # KB-ATBOOT: 老 autotools 引导修复（knowledge/tools/kb-atboot/README.md）
    src = os.path.join(self.source_folder, "srf-0.1+dfsg")
    for f in ("config.guess", "config.sub"):
        shutil.copy(os.path.join(kb_vendor, f), os.path.join(src, f))
        os.chmod(os.path.join(src, f), 0o755)
    cf = os.path.join(src, "configure")
    txt = open(cf).read().replace("umask 077", "umask 022")
    open(cf, "w").write(txt)
    apply_conandata_patches(self)
    # mtime 对齐（E248）
    for am in glob(os.path.join(src, "**", "Makefile.am"), recursive=True):
        os.utime(am[:-3] + ".in", ns=(os.stat(am).st_mtime_ns,) * 2)
    autotools = AutotoolsToolchain(self)
    ...
```
