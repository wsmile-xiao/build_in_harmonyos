# kytea 0.4.7 适配笔记

## 上游概况

KyTea（Kyoto Text Analysis Toolkit，phontron.com，Apache-2.0）是日语分词/
注音/词性标注工具包，同时提供：

- **libkytea**（C++ 库，默认 shared+static，无第三方运行时依赖，纯 STL）
- **kytea**（分析 CLI：用已训练模型对文本分词/注音）
- **train-kytea**（训练 CLI：从标注语料训练模型）
- **api-example**（API 示例程序）

构建系统：Autotools（tarball 已含生成的 configure/Makefile.in）。
源码：`https://www.phontron.com/kytea/download/kytea-0.4.7.tar.gz`
SHA256：`534a33d40c4dc5421f053c71a75695c377df737169f965573175df5d2cff9f46`

## OHOS AArch64 适配要点（按根因）

### 1. 陈旧 config.h → 必须 in-source 构建（本项目特有）

tarball 里带有维护者机器上生成的 `src/include/kytea/config.h`，其中定义
`HAVE_BOOST_TR1_UNORDERED_MAP_HPP` 等。configure 探测后重写的是
`config.h`（builddir 下）；VPATH 构建时 `#include <kytea/config.h>` 在
include 路径上只能找到源码树里的**陈旧**文件（`-I$(top_builddir)/src/include/kytea`
只能使裸 `<config.h>` 生效），于是拉入不存在的 boost/tr1 头直接编译失败。

修复：配方用 `basic_layout`（in-source configure），config.status 直接
**覆盖**陈旧 config.h，boost 定义清零。无需源码补丁。此前探针在 VPATH
下反复失败的真正根因即此，与编译器无关。

### 2. configure "cannot run C compiled programs" → HMDFS umask 问题

configure 的临时目录创建用 `umask 077 && mktemp -d ./confXXXXXX`。HMDFS
拒绝限制性权限目录创建，mktemp 失败后 configure 误报为“无法运行编译的
C 程序”。补丁 0002 把两处 umask 077 改为 022，探测通过。

### 3. config.guess/config.sub 2011 版不识别 aarch64/ohos → 补丁 0001

- config.guess 增加 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`
- config.sub 三处增加 `aarch64` CPU 与 `linux-ohos` OS 识别

修复后 build==host==aarch64-unknown-linux-ohos，configure 判定 native
（cross_compiling=no），`make check` 可直接运行测试二进制。

### 4. clang-15 收窄错误 → 补丁 0003

`src/lib/string-util.cpp` 两处 `char arr[2] = { c, 0 }`（c 为整型），
clang-15 默认 `-Werror=c++11-narrowing` 拒绝，补 `static_cast<char>`。

### 5. 上游测试写 /tmp → 补丁 0004（TMPDIR）

`src/test/test-analysis.h` 写 `/tmp/kytea-toy-corpus.txt` 等训练语料与
模型文件。OHOS `/tmp` 只读，测试必挂。补丁引入 `tmpFile()` helper 尊重
`$TMPDIR`；`conan create` 环境的 TMPDIR 指向可写目录，测试通过。

### 6. OHOS 无 /bin/sh → CONFIG_SHELL 用绝对路径 bash

configure 早期会 `exec $CONFIG_SHELL` 自我重启，libtool 也用
`$CONFIG_SHELL` 写包装脚本 shebang（内核要求解释器为**绝对路径**，
`#! bash` 直接 bad interpreter）。配方里 `shutil.which("bash")` 解析出
绝对路径再内联 `CONFIG_SHELL=<abs> <abs-bash> ./configure`，避免 profile
buildenv 里硬编码路径在各 worker 不一致的问题。

### 7. 相对路径模型文件在 HMDFS 上二次打开失败

`train-kytea -full corpus -model model.bin`（相对名）训练完成后模型文件
为 0 字节——训练阶段 open(O_CREAT) 正常，写模型时按相对名重新打开失败。
消费者测试用**绝对路径**模型名规避（CLI 层面的问题，不影响库 API）。

## 上游测试（make check）

`make check` 执行 `src/test/test-kytea`（automake 汇总为 1 个 TESTS 条目，
内部 6 个套件 / 47 个用例，输出 `**** passed ****`）：

| 套件 | 用例数 |
|---|---|
| TestKytea（特征抽取） | 10 |
| TestAnalysis（训练/预测） | 15 |
| TestSentence | 1 |
| TestCorpusIO（语料 IO） | 9 |
| TestCorpusIOEuc | 6 |
| TestCorpusIOSjis | 6 |

本机（OHOS worker）实测：`PASS: test-kytea`，`# TOTAL: 1 / PASS: 1`，
47/47 全过。

## 消费者测试（test_package）

- **库**：test.cpp 链接 libkytea，走 StringUtilUtf8 类型映射、
  FullCorpusIO 标注语料解析、Kytea 训练+分词预测（8 断言）。
  注意 `Kytea::~Kytea()` 会接管 `delete config_`，消费者不可重复 delete。
- **CLI**：上游训练与分析是**两个**入口——`train-kytea -full <corpus>
  -model <绝对路径>` 训练，再 `kytea -model <model> <raw>` 分析
  （校验分词/注音输出；分析模式的 kytea 不接受 -full 等训练参数）。

## 构建命令

```bash
conan create archives/k/kytea/0.4.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
