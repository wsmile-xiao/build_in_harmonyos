# 纯 shell 工具适配：getopt / kyua-atf / scanelf 三类外部命令缺失的等价替换链

> 草稿（DRAFT）。与同目录 `DRAFT-9200-lddtree-shell-tool-portability.kv` 成对。

## 现象

lddtree 1.27（上游 https://github.com/ncopa/lddtree ）是一个纯 POSIX shell 工具，
本平台适配时先后撞到三类**外部命令**缺失，每一类单独出现都会让「工具不可用」或
「上游测试跑不起来」：

```text
# 1) 选项解析：连 --version 都失败
$ sh lddtree.sh -V
lddtree.sh: invalid option -- 'V'          # GNU getopt(1) 不存在

# 2) 测试驱动：make check 无法运行
$ make check
kyua: command not found                     # 无 kyua，也无 atf-sh

# 3) 运行时后端：工具无法解析任何 ELF
$ lddtree.sh /bin/sh
lddtree.sh: This tool needs either scanelf or binutils (objdump and readelf)
```

另外附带两个**通用坑**（与具体软件无关，见「适用的通用坑」一节）：

```text
ERROR: lddtree/1.27: Error in source() method, line 81
        get(self, **self.conan_data["sources"], strip_root=True)
        BadZipFile: File is not a zip file

lddtree/1.27:   bmake: no system rules (sys.mk).
lddtree/1.27:   bmake: stopped in /…/b
```

## 根因

三类缺失都是**平台不提供该外部命令**，而不是配方参数问题：

| # | 缺失命令 | 上游用途 | 本平台现状 | 能否 `tool_requires` 补齐 |
|---|---------|---------|-----------|--------------------------|
| 1 | GNU `getopt(1)` | 解析 `-a/-h/-l/-R/-V/-x` 与长选项 | `/system/bin` 是 toybox，**不提供 getopt** | ❌ 制品仓无 util-linux |
| 2 | `kyua` + `atf-sh` | 以 ATF 框架驱动 `tests/lddtree_test` 的 13 个用例 | 二者均不存在 | ❌ 制品仓无这两个包 |
| 3 | `scanelf`（pax-utils） | ELF 依赖解析后端（可回退 `objdump`+`readelf`） | pax-utils 未适配发布；CI worker PATH 也不含 `objdump`/`readelf` | ⚠️ `binutils` **有**，但必须声明为运行时依赖（见下） |

关键判据：**先确认「制品仓有没有」再决定手段**。第 1、2 类制品仓确实没有，
只能改代码（打补丁）；第 3 类制品仓有 `binutils`，属于「声明依赖」而非「改代码」。

第 3 类的坑点在于依赖**类型**：lddtree 是给终端用户跑的命令行工具，
若把 binutils 声明成 `tool_requires`，构建期能过、但用户 `conan install` 后
拿到的仍是一个「找不到后端」的废工具——必须用 `requires`（运行时依赖），
靠其 `runenv_info` 把 `objdump`/`readelf` 注入 PATH。

## 正确做法

### 1) 外部 `getopt` → 等价 POSIX shell 解析（改源码）

保持全部可观测行为，不引入 bashism（无数组 / `[[ ]]` / `source`）：

- 短选项捆绑：`-la`、`-R<arg>`；
- 长选项两种写法：`--root <v>` 与 `--root=<v>`；
- `--` 终止符；
- `-h/--help` → usage 到 **stdout** 且 exit 0；
- 无参数 / 未知选项 / 缺参数 → usage 到 **stderr** 且 exit 1。

参考 `patches/0001-portable-option-parsing.patch`（73 行，仅改 `lddtree.sh`）。

### 2) ATF + kyua → 自带最小 ATF 兼容层（改测试驱动，不动测试文件）

**不要改上游测试用例**。正确做法是保留 `check` 目标、另写一个 runner，
让上游 `tests/*_test` 与 `test_env.sh` **一字节不改**即可运行：

```
check: lddtree.sh tests/lddtree_test tools/atf-sh-mini
	sh tools/atf-sh-mini tests/lddtree_test
```

`tools/atf-sh-mini`（POSIX sh，约 160 行）需实现的 ATF API 与语义：

- `atf_get_srcdir` / `atf_test_case` / `atf_add_test_case`；
- `atf_check`：`-s exit:N`、`-o match:`、`-o not-match:`、`-e match:`（可多次出现），
  未给 `-o`/`-e` 时按 ATF 默认要求该流为空；
- `atf_fail` / `atf_skip`（skip 计为 skipped，**不是** pass）；
- 每个用例**独立进程 + 独立临时工作目录**；
- 输出用例级汇总 `N tests, N passed, N failed, N skipped`，
  并额外输出断言级汇总 `ASSERTIONS: total=<N> failures=<M>`（本仓「实测 assertions=N
  failures=0」的交付口径需要它），任一失败即非零退出。

> 用 `diff` 证明改动**只新增计数与驱动代码**，未触及任何 `atf_check` 判定。

### 3) 缺 ELF 后端 → 把 binutils 声明为**运行时**依赖

```python
def requirements(self):
    # 不是 tool_requires：最终用户也要用得上
    self.requires("binutils/2.46.0")
```

### 4) 让 build() 把测试结果卡死（防「红测试绿色构建」）

`build()` 里跑 `make -r check` 后，必须**同时**校验三类汇总：退出码、用例级、
断言级；任一不合格抛 `ConanException`，并把完整记录回显进日志（CI 的 L1b/L1c
按日志判「测试是否真的执行」）。

## 不要怎么做

- ❌ **不要为了让补丁「看起来干净」而放松 `atf_check` 判定**、加 `atf_skip` 分支、
  或删改用例——上游测试文件必须逐字节可核（本案例把
  `tests/lddtree_test` / `tests/test_env.sh` 的 sha256 写进 `test_package/MANIFEST.yml` 佐证）。
- ❌ **不要用 `tool_requires` 装运行时后端**：构建期能过，用户侧仍是废工具。
- ❌ **不要在测试 harness 里偷偷注入平台环境补偿**（例如给 runner 加 PATH 兜底去补
  `getopt`）；那会掩盖「源码其实还依赖 getopt」的事实。环境依赖要在**补丁**里以
  树内、平台中立的方式解决。
- ❌ **不要为了让计数好看而跳过/早退用例**：断言总数应与不破坏时一致
  （本案例 21 保持不变，破坏行为后 `failures=8` 精确吻合 5 个失败用例的失败次数）。

## 适用的通用坑

### 坑 1：`BadZipFile: File is not a zip file`

`conandata.yml` 的 source URL 若以**裸 git tag** 结尾：

```yaml
url: "https://codeload.github.com/ncopa/lddtree/tar.gz/refs/tags/v1.27"   # ❌ get() 当 zip 解压
url: "https://github.com/ncopa/lddtree/archive/refs/tags/v1.27.tar.gz"    # ✅ 以 .tar.gz 结尾
```

Conan 的 `get()` 依据**文件名的后缀**选择解压器，无 `.tar.gz` 后缀时按 zip 处理
gzip 流并抛 `BadZipFile`。实测两种 URL 的字节数与 sha256 完全一致
（2178596 字节 / `f24b1965…`），改 URL 不影响校验和。

### 坑 2：制品仓 bmake 需 `make -r`

制品仓 `bmake/20200710` 的 `sys.mk` 位于 `<pkg>/share/mk/sys.mk`，而 bmake
默认不在该目录搜索系统规则文件，因此在**读取项目 Makefile 之前**就中止：

```
bmake: no system rules (sys.mk).
```

用 `make -r`（禁用内建规则）即恢复；lddtree 的 Makefile 显式声明了全部规则，
且 `-r` 同样被 GNU make 接受，故该写法可移植。

### 坑 3：CI 预下载会改写 `conandata.yml`（务必还原）

`ci/conan/build_and_test.sh` 会把官方 URL 改写成 `gh-proxy.com` 前缀**列表**
供自身预下载使用。**该状态若被提交将触发 PF7 硬闸（镜像前缀 = R39 违规）**。
凡跑过 `build_and_test.sh`（或进程被中途杀死导致 trap 未还原），提交前必须
`grep -n 'url:' conandata.yml` 复核为官方单一 URL。

### 坑 4：CI 的 L4 对纯 shell 项目会误报「危险函数」

门禁实现为 `grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/`，**缺词首边界**，
会命中补丁注释里普通英文词 `targets` 中的子串 `gets`。纯 shell 项目根本没有 C 代码，
属误报；`L4` 为 warn 级、非阻塞，如实登记即可，不必为它改代码。

## 适用范围

- 所有**纯 shell / 脚本型**（无编译步骤）的归档包，尤其是上游自带
  ATF/kyua/shellcheck 等 Linux 发行版专属测试框架的项目；
- 任何需要外部命令做「解析后端」的薄封装工具（后端必须声明为运行时依赖）；
- 坑 1/坑 2/坑 3 与软件无关，适用所有走 Conan 的包。

## 证据

lddtree 1.27，本地 `conan create` + 本地同脚本 CI 模拟 + 远端 CI：

- 上游套件：`13 tests, 13 passed, 0 failed, 0 skipped` / `ASSERTIONS: total=21 failures=0` / exit 0；
- 消费者测试：`ASSERTIONS: total=38 failures=0` / exit 0；
- 隔离 PATH（**无 getopt**、有 readelf/objdump）下 `make -r check` 仍 13/13
  → 证明补丁 0001 真正移除了 getopt 依赖，且 0002 未偷偷注入环境补偿；
- 破坏性反向验证：故意把 interpreter 输出改为固定 `BOGUS` →
  `13 tests, 8 passed, 5 failed` / `ASSERTIONS: total=21 failures=8` / 退出码 2
  → 证明用例与计数非空转（随后还原）；
- 本地 CI：`L0 pass / L1 pass / L2 pass / L5 pass`、`L4 warn`（坑 4 误报）、
  KC/JC pass、Pass rate 100.0% (1/1)；
- 远端 CI：构建 #48273 通过（Conan test_package / L0 / L1 三项通过）。
