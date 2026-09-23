# HMDFS 大小写不敏感导致 conan 解包失败的实测证据（dinit-shutdown 0.21.0）

对应知识草稿 `knowledge/drafts/E578-draft-00C9.md/.kv`。所有命令与输出均为设备原样复制；
**本文件内**的省略全部以 `...` 显式标注，逐条列出（**用可搜索标记定位，不用行号**，避免编辑后漂移）：

| # | 省略内容 | 定位标记（在本文件中 grep 可命中） |
|---|----------|-----------------------------------|
| 1 | 长 Python 列表输出的中间元素（第 2 节成员列表） | `'dinit-0.21.0/.cirrus.yml', ...,` |
| 2 | tar 回溯的中间栈帧（第 3 节） | `Traceback (most recent call last):` 与其后独立的 `  ...` 行 |
| 3 | git-archive 包说明中上游 URL 的域名与会话前缀（第 3 节） | `.../archive/refs/tags/v0.21.0.tar.gz` |
| 4 | 探针 tarball 绝对路径的中段（第 4、5 节） | `file:///.../repro/collide.tar.gz` |
| 5 | `conan create` 日志中缓存分片目录名的中段（第 5 节） | `p/dinit.../s` |
| 6 | 引用 E470 报错文本时其构建目录路径的前缀（第 7 节） | `'.../b/build/Release'` |

注意：第 4 节的探针输出 `…/p/colli6680b10c5e9bb/s` 在本文件中是**完整分片名**（未省略）；
把该分片名进一步缩写（省略其中段）的是**知识草稿** `knowledge/drafts/E578-draft-00C9.md` 第 22 行，
该草稿自身已在紧随其后的说明段声明了这处缩写。因此检索本文件的分片名标记时**不应**期待命中被缩写的形态。

另有 **4 种尖括号上下文占位**，均为命令模板本身的一部分，不是对输出的省略：
`<site-packages>`（Python 命令中的路径占位）、`<ohos-aarch64 绝对路径>`（profile 参数占位）、
`<包目录>`、`<worktree>`。（文中的方括号均为代码实体，如 `[Errno 17]`、`[^_A-Za-z]`、`["sources"]`，
不存在方括号占位符。）

Python 栈帧路径（第 3 节）为**完整原文** `/data/service/hnp/python.org/python_3.12/lib/python3.12/tarfile.py`，
未做任何省略。

## 1. 设备文件系统大小写语义

```console
$ TD=$HOME/tmp/dinit-shutdown-0.21.0/caseprobe2; mkdir -p $TD; touch $TD/Aaa; touch $TD/aaa; ls $TD
Aaa
$ stat -c '%n %i' $TD/Aaa $TD/aaa
/storage/Users/currentUser/tmp/dinit-shutdown-0.21.0/caseprobe2/Aaa 2305843009243243208
/storage/Users/currentUser/tmp/dinit-shutdown-0.21.0/caseprobe2/aaa 2305843009243243208
```

两个不同大小写的名字解析到**同一 inode** → HMDFS 大小写不敏感。`~/ws`、`~/tmp`、`~/.conan2`
全部位于 `/data/service/el2/100/hmdfs/account`（`df -T` 报 `hmdfs`），即 conan 源码缓存与构建目录
也在同一语义下。

## 2. 上游 tarball 的冲突成员

```console
$ python3 -c "import tarfile;print([n for n in tarfile.open('dinit-0.21.0.tar.xz').getnames() if n.count('/')<=1])"
['dinit-0.21.0', 'dinit-0.21.0/.cirrus.yml', ..., 'dinit-0.21.0/BUILD', 'dinit-0.21.0/CONTRIBUTORS',
 'dinit-0.21.0/LICENSE', 'dinit-0.21.0/Makefile', 'dinit-0.21.0/NEWS', 'dinit-0.21.0/README.md',
 'dinit-0.21.0/TODO', 'dinit-0.21.0/build', 'dinit-0.21.0/configs', 'dinit-0.21.0/configure', ...]
```

`BUILD`（文档文件）在成员序中先于 `build/`（目录）出现；`dinit-0.21.0/build/` 内含
`Makefile`、`includes`、`tools`、`version.conf`，是构建必需项。

## 3. Python tarfile 层复现（修复前）

对本包 `conandata.yml` 声明的官方 release 制品 `dinit-0.21.0.tar.xz` 直接解包即复现：

```console
$ python3 -c "import tarfile;tarfile.open('dinit-0.21.0.tar.xz').extractall('out')"
Traceback (most recent call last):
  ...
  File "/data/service/hnp/python.org/python_3.12/lib/python3.12/tarfile.py", line 2450, in _extract_member
    self.makedir(tarinfo, targetpath)
  File "/data/service/hnp/python.org/python_3.12/lib/python3.12/tarfile.py", line 2483, in makedir
    os.mkdir(targetpath, 0o700)
FileExistsError: [Errno 17] File exists: 'out/dinit-0.21.0/build'
```

（GitHub 自动生成的 git-archive 包 `dinit-v0.21.0.tar.gz`——`.../archive/refs/tags/v0.21.0.tar.gz`——
含同样的顶层 `BUILD` 与 `build/`，解包表现一致；本文件第 2 节的成员清单取自该包，与官方
release 制品的成员集合相同。）

同一现象用最小 tarball（成员仅 `x`、`x/BUILD`、`x/build`、`x/build/Makefile`）复现：

```console
$ python3 -c "import sys;sys.path.insert(0,'<site-packages>');from conan.tools.files.files import untargz;untargz('collide.tar.gz','out')"
FileExistsError: [Errno 17] File exists: 'out/x/build'
```

## 4. conan create 端到端复现（最小探针配方）

探针配方只调用 `get(self, **self.conan_data["sources"])`（`file://` 指向上述最小 tarball）：

```console
$ conan create . -pr:h=<ohos-aarch64 绝对路径> -pr:b=<ohos-aarch64 绝对路径>
collide-probe/0.1: Calling source() in /storage/Users/currentUser/.conan2/p/colli6680b10c5e9bb/s
collide-probe/0.1: Sources correctly downloaded from file:///.../repro/collide.tar.gz
collide-probe/0.1: Uncompressing collide.tar.gz to .
ERROR: collide-probe/0.1: Error in source() method, line 11
	get(self, **self.conan_data["sources"])
	FileExistsError: [Errno 17] File exists: './x/build'
```

失败发生在 `source()`、编译开始之前。

## 5. 修复后验证（conan 官方 API 的成员级排除）

```console
$ python3 -c "import sys;sys.path.insert(0,'<site-packages>');from conan.tools.files.files import untargz;untargz('collide.tar.gz','out2',strip_root=True,excludes=['x/BUILD'])"
成功; out2 内容: ['build']
build/ 内容: ['Makefile']
```

在本包配方中即：

```python
get(self, **self.conan_data["sources"], strip_root=True, excludes=["dinit-0.21.0/BUILD"])
```

`conan create` 的实际日志（`reports/conan-create.log` 第 83、84、85、91、95 行——五行不连续；
引用为**逐字原文**，其中下载 URL 带 CI/验证轮注入的 `ghfast.top` 镜像前缀、包引用带
`@ohpcd/stable` 后缀，`Calling source() in` 那一行路径中段的分片目录名（形如 `dinit0e194faa70426`）
按 `...` 省略，其余字符与日志原文一致）：

```text
dinit-shutdown/0.21.0@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/dinit.../s
dinit-shutdown/0.21.0@ohpcd/stable: Sources correctly downloaded from https://ghfast.top/https://github.com/davmac314/dinit/releases/download/v0.21.0/dinit-0.21.0.tar.xz
dinit-shutdown/0.21.0@ohpcd/stable: Uncompressing dinit-0.21.0.tar.xz to .
dinit-shutdown/0.21.0@ohpcd/stable: Copying sources to build folder
dinit-shutdown/0.21.0@ohpcd/stable: Calling build()
```

（提交版 `conandata.yml` 里 `sources.url` 是**单条官方 URL**；`ghfast.top` 前缀是 conan-verify 为规避
CI 出网限制临时注入、随后自动还原的镜像形态，未进入任何提交。）

## 6. 被排除文件不参与构建的检索证据

```console
$ grep -rnE '(^|[^_A-Za-z])BUILD([^_A-Za-z]|$)' Makefile src/Makefile build/Makefile src/tests/Makefile doc/manpages/Makefile configure
configure:377:See BUILD file for more information.
configure:755:# See BUILD for help on all variables.
```

两处均为 configure 的帮助/注释文本，无构建规则把该文件作为输入；排除后 `make -C build`、
`make -C src dinit-shutdown`、`make -C src check` 全部成功（见 `reports/upstream-tests-native.log`）。

## 7. 与 E470 的阶段差异（反证）

E470 的失败在 generate/build 阶段（`NotADirectoryError: [Errno 20] Not a directory: '.../b/build/Release'`，
cmake 建构建目录时撞上仓库根的 Bazel `BUILD` 文件），修法是换构建目录名。本条目在第 3/4 步即
失败——`cmake`/`make` 尚未被调用，构建目录配置无从生效，因此换构建目录名的修法对本题无效；
反之 `excludes` 修法也不覆盖 E470 的构建期冲突。
