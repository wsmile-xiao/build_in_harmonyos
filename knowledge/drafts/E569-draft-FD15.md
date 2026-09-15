# E569 — 上游 Makefile.in 写死 in-tree 相对 include 路径，out-of-tree 构建头文件找不到

## 错误特征

编译期报找不到**本工程自己的**头文件（不是依赖库的头文件，这点是识别关键）：

```
src/util/bitvector.c:12:10: fatal error: 'util/bitvector.h' file not found
```

翻构建日志可见失效的 include 路径：

```
-I../../src/include
```

而该相对路径是从 build 目录出发的，解析结果指向一个**不存在的目录**（conan 的 layout 把 build 与 source 分离，`build-release/src/include` 是空镜像）。

## 触发条件

- 构建系统: autotools（`src/*/Makefile.in` 内手写的相对 `-I`）
- 阶段: make
- 环境: conan / CI 的 out-of-tree 构建；手工 in-tree 编译 **不复现**（这是"本地过、CI 挂"的典型成因）
- 观察: 报错头文件属于本项目源码树

## 根因分析

老 autotools 工程在 `src/util/Makefile.in` 里直接用裸相对路径 `-I../../src/include` 表达"回到源码树"，而未使用 automake 提供的 `$(top_srcdir)` 变量。这个写法隐含"构建目录 == 源码目录"这一 in-tree 假设。

conan 2 的 cpp/autotools layout 默认把构建目录独立到 `build-<config>/`，相对路径的基准变了：`../../src/include` 不再落在源码树，而是落到 build 目录的兄弟位置。Makefile 不做校验，clang 报 file not found。

值得注意的是 patch 掉 Makefile.in 并非唯一解：include 根是"编译器找头文件的搜索路径"，属于 CFLAGS 语义，可以从配方侧用绝对路径补齐，避免维护一个只为路径服务的补丁。

## 解决方案

### 推荐方案

在 `generate()` 中用绝对路径补齐 include 根（cpu 1.4.3 实测有效）：

```python
tc = AutotoolsToolchain(self)
tc.extra_cflags.append(f"-I{self.source_folder}/src/include")
```

`extra_cflags` 会进入 CFLAGS，与 Makefile 自带的 `-I` **叠加且顺序无关**（clang 按序全部搜索），因此无需改上游文件。

### 禁止做法

- ❌ 在 build 目录里造一个空的 `src/include` 目录（或复制头文件）制造"路径存在"的假象——CI 干净环境下不可复现
- ❌ 用 `--srcdir` 等参数强行把构建目录掰回源码树（绕过而非适配，且会连带破坏其他规则）
- ❌ 只 patch 掉当前报错的那一个 Makefile.in 就收手——同类相对路径往往成片存在，应先 `grep -rn '\-I\.\./\.\.' src/*/Makefile.in` 清点

## 验证

```bash
# 1. 清点同类隐患
grep -rnE '\-I\.\./\.\.' src/*/Makefile.in
# 2. 构建日志中 include 路径应为绝对路径
grep -o '\-I[^ ]*src/include' build-release/compile.log | sort -u
# 3. 端到端
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify cpu 1.4.3
```

## 关联条目

- 相关: E568（同为"交叉/分离布局下语义失效"，对策形态不同）
- 相关: E571（同为 out-of-tree 假设，发生在 install 阶段）
- 相关: E007（平台探针层）
