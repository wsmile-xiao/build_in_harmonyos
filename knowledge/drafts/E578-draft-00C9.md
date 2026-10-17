# E578 — HMDFS 大小写不敏感：tarball 顶层 BUILD 文档与 build/ 目录冲突，conan 解包在 source 阶段失败

## 错误特征

`conan create` 的 **source 阶段**（编译尚未开始）报 `FileExistsError`，报错名字是目录名而磁盘上
它是普通文件。下面两条都是**设备上真实捕获**的输出，分别来自 Python 解包层与 conan 端到端层：

Python 解包层（直接对 dinit 0.21.0 官方 release tarball 调用 `tarfile.extractall`）：

```text
File "/data/service/hnp/python.org/python_3.12/lib/python3.12/tarfile.py", line 2450, in _extract_member
    self.makedir(tarinfo, targetpath)
File "/data/service/hnp/python.org/python_3.12/lib/python3.12/tarfile.py", line 2483, in makedir
    os.mkdir(targetpath, 0o700)
FileExistsError: [Errno 17] File exists: './dinit-0.21.0/build'
```

conan 端到端层（最小探针配方，`conanfile.py` 只调用 `get(**conandata.sources)`；
tarball 内只有 `x`、`x/BUILD`、`x/build`、`x/build/Makefile` 四个成员）：

```text
collide-probe/0.1: Calling source() in /storage/Users/currentUser/.conan2/p/colli.../s
collide-probe/0.1: Sources correctly downloaded from file:///.../repro/collide.tar.gz
collide-probe/0.1: Uncompressing collide.tar.gz to .
ERROR: collide-probe/0.1: Error in source() method, line 11
	get(self, **self.conan_data["sources"])
	FileExistsError: [Errno 17] File exists: './x/build'
```

> 说明：dinit-shutdown 0.21.0 的配方自始即带 `excludes` 修复，因此**没有**该包的失败日志
> （`git show 41b45c3362:archives/d/dinit-shutdown/0.21.0/conanfile.py` 已含 `_SOURCE_EXCLUDES`
> 与 `excludes=_SOURCE_EXCLUDES`，且该文件自首次提交起未改动）。上表两条是本条目唯一的真实失败记录，
> 且与 `archives/d/dinit-shutdown/0.21.0/reports/hmdfs-case-collision-evidence.md` 第 3、4 节同源一致
（探针段落中缓存分片目录名在本草稿进一步缩写为 `colli.../s`，完整分片名见该证据文件第 4 节）。
> 引用保真：Python 栈帧两条为**完整路径原文**（不再省略）；最小探针引用中两处以 `...` 省略，
> 省略内容均为缓存分片目录名/探针 tarball 绝对路径的中段：
> ① `/storage/Users/currentUser/.conan2/p/colli.../s`（省略分片目录名中段）；
> ② `file:///.../repro/collide.tar.gz`（省略探针 tarball 绝对路径中段）。
> 除上述两处外，所有字符均为设备输出原文。

特征：错误发生在 `source()`/`Uncompressing ...` 之后、任何编译行之前；报错文件名是**目录名**
（`build`），而磁盘上该名字实际是一个**普通文件**（`BUILD`）；换成大小写敏感机器构建同一 tarball
不报错，因此同一 PR 的 CI worker 全绿而设备必失败。

## 触发条件

- 构建系统: 任意（本例为上游自带 `configure` + `Makefile` 的 custom 工程；与构建系统无关）
- 阶段: `source()` 解包（download + untargz 之后，`build()` 之前）
- 平台: HarmonyOS PC 设备工作区（HMDFS，`/storage/Users/currentUser` 下全部目录，含 `~/.conan2` 缓存）
- 上游特征: tarball 在同一层目录内存在大小写仅异名的成员对，且**文件成员出现在目录成员之前**才能复现该异常形态
  （本例 `BUILD` 在 tar 成员序中位于 `build` 之前）

## 根因分析

1. HMDFS 大小写不敏感：`touch AAA` 后 `stat aaa` 与 `AAA` 返回同一 inode（实测 inode
   `2305843009243243208`，两个名字各出现一次但 inode 相同）。
2. 上游 dinit 0.21.0 release tarball 顶层同时含 `BUILD`（构建说明文档）与 `build/`（构建系统目录，
   内含 `Makefile`/`includes`/`tools`/`version.conf`）。
3. Python `tarfile._extract_member` 处理目录成员时调用 `makedir` → `os.mkdir(targetpath, 0o700)`；
   在大小写不敏感 FS 上 `build` 与已存在的普通文件 `BUILD` 是同一条目录项，`os.mkdir` 抛 `EEXIST`。
   `makedir` 的 `except FileExistsError` 分支用 `os.path.isdir(targetpath)` 判定，对普通文件返回假，
   于是重新抛出，异常穿透 conan 的 `untargz()`/`unzip()`/`get()`。
4. 结论：这不是源码或配方缺陷，而是「设备文件系统语义 × 上游 tarball 成员命名」的确定性冲突；
   补丁机制无法参与（补丁在解包成功之后才应用）。

## 解决方案

### 推荐方案

在解包成员层排除冲突成员（仅当该成员不参与构建时）：

```python
# conanfile.py
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True,
        excludes=["dinit-0.21.0/BUILD"])
```

要点：

- `excludes` 走 `untargz()` 的成员过滤分支（设置 `excludes`/`pattern`/`strip_root` 之一即跳过
  `extractall()` 快速路径），因此冲突成员不会进入 `extractall(members=...)`，`EEXIST` 不再发生。
- `strip_root=True` 可与 `excludes` 同时使用（成员名先过滤后去根目录）。
- 排除项必须不参与构建：`BUILD` 是纯文档。实测检索（精确边界，避免命中 `BUILD_SHUTDOWN` 变量）：

  ```text
  $ grep -rnE '(^|[^_A-Za-z])BUILD([^_A-Za-z]|$)' Makefile src/Makefile build/Makefile \
      src/tests/Makefile doc/manpages/Makefile configure
  configure:377:See BUILD file for more information.
  configure:755:# See BUILD for help on all variables.
  ```

  两处都只是 configure 的帮助/注释文本，没有任何构建规则把该文件当输入（同一次 `make` 在文件被排除后
  完整跑通，见「验证」节第 3 步及 dinit-shutdown 0.21.0 的 conan create 日志）。
- 设备与 CI 都执行同一排除，源码树逐字节一致，不掩盖平台差异。
- 冲突成员若属构建必需（例如目录 `build/` 本身必须先被创建），改用非默认构建目录名
  （见 E470 的 `cmake_layout(build_folder=...)` 思路）或改到大小写敏感的工作区构建。

### 禁止做法

- ❌ 在 `build()`/`package()` 里 `rm`/改名冲突文件——那些动作发生在解包之后，对 `EEXIST` 无效。
- ❌ 用 `core.ignorecase=false` 冒充文件系统已支持大小写——只影响 git 索引。
- ❌ 通过补丁删除/改名上游文件来绕过——补丁应用在解包成功之后，路线不成立。
- ❌ 把该失败当成源码或配方问题反复调参——第一条真实错误已指向文件系统语义。

## 验证

```bash
# 1. 判定设备文件系统大小写语义（True 即不敏感）
python3 -c "import os;open('AAA','w').close();print(os.path.exists('aaa'))"

# 2. 直接复现（Python tarfile 层）
python3 -c "import tarfile;tarfile.open('dinit-0.21.0.tar.xz').extractall('out')"
#  -> FileExistsError: [Errno 17] File exists: 'out/dinit-0.21.0/build'

# 3. 修复后（conan API 层）
python3 -c "import sys;sys.path.insert(0,'<site-packages>');from conan.tools.files.files import untargz;untargz('collide.tar.gz','out2',strip_root=True,excludes=['x/BUILD'])"
ls out2           # -> build
ls out2/build     # -> Makefile
```

实测结果（dinit-shutdown 0.21.0，设备 `$HOME/.conan2` 缓存）：修复后 `conan create` 的
source 阶段输出 `Uncompressing dinit-0.21.0.tar.xz to .` 且不再报错，构建进入 configure/compile；
解包出的源码树含 `build/Makefile` 而不含 `BUILD`。

## 与既有条目的差异（含反证命令与实测输出）

- **E470**（cppitertools 2.3）同样是「大小写不敏感 FS 上 `BUILD` 文件与 `build` 目录冲突」，
  但阶段与机制不同：E470 失败在 **generate/build 阶段**——`cmake_layout` 默认 `build` 目录与仓库根
  的 Bazel `BUILD` 文件冲突，报 `NotADirectoryError: [Errno 20] Not a directory: '.../b/build/Release'`，
  修法是 `cmake_layout(self, build_folder="build_dir")` 换构建目录名。
  本条目的失败发生在更早的 **source 解包阶段**（`get()`/`untargz()`），错误类型是
  `FileExistsError: [Errno 17]`（`os.mkdir` 的 EEXIST），此时任何构建目录配置都还没机会生效，
  因此 E470 的修法对本条目无效（换构建目录名不能阻止解包建 `build/` 目录）。
  反证命令：见上文「验证 2/3」两段——同一 tarball 在同一设备上，仅解包即失败；
  加上 `excludes` 后解包成功（输出 `build`、`build/Makefile`），全程未触及 cmake/make。
- **E193**（HMDFS 大小写不敏感导致测试用例失败）描述的是测试期行为差异，不涉及 tarball 解包冲突。
- 本条目新增的可复用增量：把「解包期冲突」与「构建期冲突」区分开，并给出 conan 官方 API
  （`get(excludes=...)`）的成员级排除修法及其适用边界（被排除成员必须非构建必需）。

## 关联条目

- 相似: E470（大小写不敏感 FS 的 BUILD/build 冲突，但为构建目录阶段）
- 原则: P016（HMDFS 文件系统限制必须用替代方案）
