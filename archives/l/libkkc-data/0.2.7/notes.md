# libkkc-data 0.2.7 编译笔记

## 编译信息
- 软件名称：libkkc-data（libkkc 的日语假名-汉字转换语言模型数据）
- 版本：0.2.7
- 下载 URL：https://github.com/ueno/libkkc/releases/download/v0.3.5/libkkc-data-0.2.7.tar.xz
- sha256：`9e678755a030043da68e37a4049aa296c296869ff1fb9e6c70026b2541595b99`
- 构建系统：python3（上游 configure/make 只是两层薄封装，真正的构建是
  `data/models/Makefile.am` 中 `sorted3-data.stamp` 目标对两个 Python 工具的调用）

## 包内容（安装到 `$PREFIX/lib/libkkc/models/sorted3/`）
| 文件 | 大小 | sha256 |
|------|------|--------|
| data.input | 269,624 | 5E3CBF0E40AEB01692A66244E08A237148C5FF0FF41EBE4ECB6D6308C99F997A |
| data.1gram.index | 1,167,040 | 30276087EAA39109DAB10526C3FF18D20724B286C8618D4B7B6B70A7B605BA7A |
| data.1gram | 709,998 | 9103A8156DE0D7D94D5DB59AAA49F44101242F4F16409AF125DE11B8AEF302B9 |
| data.2gram | 9,304,968 | 7FC84A2EC66846A7F557676C67BAE686BC31131D6081EF7FDC25789CCCE2AEAE |
| data.2gram.filter | 643,968 | 642F7F10E52F000A54216EAA97084F77F5C0EF75E5D564B89D312B5AAAAA6CCA |
| data.3gram | 17,768,780 | 901D447EC7564EE21243444557784ADD17D83E4AE0EC8929C24261B3A4F5C3E1 |
| data.3gram.filter | 1,475,666 | 32492D9A8832E7AFC9D1F0A7501B2545D3AE33368B6EF7027C27883C1E0C476C |
| metadata.json | 102 | CFE7E8F16A19BEEAB0AA61FB8DF83517CA50BCE5C70331286C6A3596E12CAB07 |

生成是确定性的：8 个文件与已验证的参考输出逐字节一致（大小 + sha256 完全相等），
`test_package/test_verify.py` 即以这份参考值为断言。

## 关键问题与解决方案

### 1. OHOS worker 无法 dlopen 用户路径的 .so（E212）→ marisa 改为进程外调用
首版方案把 marisa 编译成 CPython 扩展 `_marisa.so` 再由 `tools/sortlm.py`
`import marisa` 使用。该方案在真机/WSL 可用，但在 CI worker 上失败：

```
libkkc-data/0.2.7: RUN: ".../python3" -B -c "import marisa; ..."
  File ".../build-release/pymod/marisa.py", line 1, in <module>
    import _marisa
ImportError: Error loading shared library .../pymod/_marisa.so: Permission denied
```

**根因**：OHOS 的 hmmac 按路径分配安全标签——`/data/service/hnp` 下的文件是
`hnp_file` 标签，用户可写路径（`/storage/Users` = hmdfs，`/data/storage/el2/base` =
hishell_hap_data_file）是别的标签；沙箱只允许进程加载 `hnp_file` 标签的共享库。
构建产物必然落在用户路径，因此进程内扩展模块在 CI 上不可用，与文件权限、
签名、`chmod` 无关（见知识库 E212；pycairo/nanobind/rdiff-backup 同为该限制）。

**解决**：把 marisa 调用移出解释器——新增 `bindings/marisa_tool.cc`，
与 marisa 0.3.1 源码在**同一条编译命令**里编成**独立可执行文件**（进程启动不受
标签限制，与仓库内 `marisa/0.3.1` 的 `cmake.test()` 执行测试二进制同理）：

```
marisa_tool build <keys-file> <trie-file> [--no-ids]
    <keys-file>  按插入顺序排列的 key（每行一个，UTF-8）
    <trie-file>  由 marisa::Trie::save() 写出，与上游 trie.save() 逐字节相同
    stdout       每行 "<id>\t<key>"（不加 --no-ids 时），供 Python 建立 key→id 映射
marisa_tool selftest
    构建 3 key 的小 trie 并核对 id；配方在生成前用它做“helper 能否运行”的探针
```

`patches/0002-marisa-tool.patch` 把 `sortlm.py` 中三处 marisa 用法替换为
子进程调用，其余逻辑（N-gram 解析、量化、三个数据文件的写出）保持上游不变：
- `Keyset.push_back` → 收集 key 列表写临时文件；
- `Trie.build/save` → `marisa_tool build`（一次调用同时建表并落盘）；
- `Trie.lookup + Agent.key_id` → 读取 helper 输出的 key→id 映射做字典查询。
默认 config flags 与上游 `Trie().build(keyset)` 相同，因此 trie 字节与 id 完全一致。

**验证（本地 Windows 全流程复跑）**：vocab trie 118,333 keys、input trie 117,901 keys，
sortlm 35.7s、全流程 86.3s；8 个产物文件大小 + sha256 与上表逐项相等（含
`data.1gram.index` / `data.input` 两个 marisa trie 二进制）。

### 2. 上游工具是 Python 2 代码（补丁 0001）
sortlm.py / genfilter.py 使用 `print` 语句、`iteritems()`、`sorted(..., cmp=)`、
整数除法、`xrange`、文本模式读写二进制等 Python 2 特性。
`patches/0001-python3-compat.patch` 将其移植到 Python 3：
- `print` → `print(...)`；`iteritems()` → `items()`；
  `sorted(items, cmp=cmp_header)` → `sorted(items, key=lambda item: item[0])`（按打包后的头部字节排序，语义不变）；
- 整数除法 `//`、`range()`；
- genfilter 输入输出改为二进制模式，直接写 `bytearray`；
- sortlm 输入以 UTF-8 文本打开；
- 跳过引用了不在 unigram 词表中的词的退化了 n-gram 行（`len(ids) != n` 时 continue），
  避免 3-gram 段 `bigram_offsets[(ids[0], ids[1])]` 的 KeyError。
- 上游较新的 configure 已基于 sysconfig 的 `AM_PATH_PYTHON`，Python 3 可直接运行，无需补丁。

### 3. 数据生成 = 官方构建命令
数据不使用预生成产物（R19；上游 tarball 的 `data/models/sorted3/` 只带
`metadata.json`，模型文件全部由构建期生成）。recipe 的 `build()` 直接执行上游
`data/models/Makefile.am` 中 `sorted3-data.stamp` 的三条命令（`python -B $(PYTHON)...`）：
```
python -B tools/sortlm.py --marisa-tool <helper> data/models/text3/data.arpa <build>/sorted3/data
python -B tools/genfilter.py <build>/sorted3/data.2gram <build>/sorted3/data.2gram.filter 12
python -B tools/genfilter.py <build>/sorted3/data.3gram <build>/sorted3/data.3gram.filter 10
```
并拷贝 `metadata.json`。`package()` 把 `sorted3/*` 安装到 `lib/libkkc/models/sorted3/`，
`cpp_info.resdirs = ["lib"]`。

### 4. marisa 源码：按 sha256 固定的上游 tarball 构建，而非 vendored 副本
helper 需要 marisa 的实现。做法是在 `conandata.yml` 的 `marisa_sources` 中固定
官方 tag 归档，由 `source()` 解到 `build-tools/marisa-trie/`：

```
url:    https://github.com/s-yata/marisa-trie/archive/refs/tags/v0.3.1.tar.gz
sha256: 986ed5e2967435e3a3932a8c95980993ae5a196111e377721f0849cad4e807f3
```

**为什么不是 vendored 副本**：早先版本把上游 41 个文件（6,117 行）整份拷进
`bindings/marisa-src/`（`include/`→`hdr/`、`lib/`→`src/` 改名）。这让单个 PR 膨胀到
7,122 行 / 54 个文件——AI 代码检视因「变更过大」直接跳过审查，仓库里也长期存着一份
需要单独同步的上游副本。改为按 sha256 取官方源后，同样的字节内容不再入库：
41 个文件已逐一校验与官方 v0.3.1 tarball **逐字节一致**，因此生成的模型数据不变。

**为什么不是 `tool_requires marisa/0.3.1`**：制品仓里确实有 ohos-aarch64 的
`marisa/0.3.1` 静态库，但 Conan 包是按 profile 的上下文解析的，而 helper 是**故意**
用「运行生成步骤的那台机器自己的编译器」编译的（本机 MinGW/WSL g++、worker 的
`/data/service/hnp/bin/clang++`）。当构建机 profile 与 ohos-aarch64 不同时，
`tool_requires` 要么找不到二进制，要么解析出一个**由别的编译器构建**的库——本机实测
默认 Windows profile 解析出的是 MSVC 的 `marisa.lib`，MinGW g++ / clang++ 根本链接不了。
取源码则保证 helper 与 trie 实现在任何构建机上都是同一次编译、同一 ABI，
且「编译 + 真跑 selftest」的验证逻辑保持不变。

### 5. helper 的编译器定位：候选枚举 + 逐个实跑自检（第二次 CI 失败后修复）
第一版 `_native_cxx()` 只做 `shutil.which("c++"/"g++"/"clang++")`。这在 CI worker 上不成立：
profile 的 `[buildenv] PATH` 只作用于 `self.run()` 派生的子进程，**不会改 conan 进程自身的
环境**，而 worker 上 CI shell 的 PATH 是
`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:/storage/Users/currentUser/.local/bin`
（见 CI 构建日志的 `environment:` 段），工具链所在的 `/data/service/hnp/bin` 不在其中。
只按 PATH 查找 → `RuntimeError: no native C++ compiler found`。

修复：`_cxx_candidates()` 按 `CXX` 环境变量 → PATH → profile conf
(`tools.build:compiler_executables`，worker 上为 `/data/service/hnp/bin/clang++`) →
已知绝对路径的次序枚举，并且**每个候选都真编译 + 真跑 `marisa_tool selftest`**，
只有能在这台机器上启动的 helper 才被采用；全部失败时抛出带完整尝试清单的错误
（而不是留下一个跑不起来的二进制）。

链接旗标同样做成候选：`-static-libstdc++` 优先（实测 OHOS clang++ 加上它之后
动态依赖从 `libc++_shared.so + libc.so` 变成只剩 `libc.so`，helper 因此不依赖
SDK lib 目录是否在加载器搜索路径上），失败再退回普通动态链接与 `-static`。

> 顺序上 PATH 优先于 profile conf：本机构建环境（如 Windows+MinGW）能立刻命中，
> 不必先撞一次交叉工具链的编译错误；worker 上 PATH 无编译器时自然落到 conf。

## 依赖
- 无 Conan 依赖（最终包只含数据文件）
- 构建期需要：一份由 `marisa_sources` 按 sha256 固定的上游 marisa-trie 0.3.1 源码，
  以及本机原生 C++ 编译器（见第 4、5 节）

## 编译状态
- 状态：built
- 功能：模型数据于构建期由官方语料生成，字节级可复现
- 补丁：0001-python3-compat.patch（工具 Python 3 移植 + 数据瑕疵行跳过）、
  0002-marisa-tool.patch（marisa 改为进程外 helper 调用）
- CI：PR #9951；首轮 `conan-build-test` 失败于进程内扩展无法 dlopen（见第 1 节），
  改为进程外 helper 后，第二轮修复了第 5 节的编译器定位问题
- 第三轮：AI 检视以「变更过大」跳过（7,122 行 / 54 文件）。改为按 sha256 取官方
  marisa 源码替代 vendored 副本（见第 4 节），PR 缩到 13 文件 / 890 行；
  41 个文件已校验与官方 tarball 逐字节一致，helper 编译 + selftest 本地复跑通过，
  生成的模型数据不变。同时移除了一处越界的仓库级改动：分支曾整份删除
  `.gitattributes`（会连带删掉 main 上 `archives/a/acpi-override/.../test_hook.sh`
  的 `eol=lf` 规则），现已恢复为与 main 一致。
---
**编译结束**: 2026-09-14
**最终状态**: built
