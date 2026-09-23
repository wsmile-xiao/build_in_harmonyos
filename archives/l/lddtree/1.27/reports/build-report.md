# 编译过程记录 — lddtree 1.27

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | lddtree |
| 版本 | 1.27 |
| 编译日期 | 2026-09-15 |
| 编译者 | OpenHarmonyPC 适配组（AtomCode 协作模式，分支 `feat/lddtree-1.27`） |
| 上游仓库 | https://github.com/ncopa/lddtree |

## 环境信息

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 / OHOS 6.0 |
| 架构 | aarch64 (armv8) |
| 编译器 | 不适用（纯 shell 项目，无 C/C++ 源码）；测试运行时使用平台 `/bin/sh` (mksh) |
| 构建系统 | makefile（仅驱动测试） |
| Conan | 2.29.1（OHOS 适配版）+ profile `ci/conan/profiles/ohos-aarch64` |

## 编译过程

### 1. 源码获取

```bash
# 官方源（GitHub release tag v1.27）
https://github.com/ncopa/lddtree/archive/refs/tags/v1.27.tar.gz
sha256 = f24b1965f5b353ad93fb2844edcb5ac7c41a7d19faec67694810fa03314ce649  (2178596 bytes)
```

> 注意：URL 必须以 `.tar.gz` 结尾。写成 `…/tar.gz/refs/tags/v1.27` 时 Conan
> `get()` 会按 zip 处理 gzip 流并抛 `BadZipFile`（实测）。

### 2. 配置

无需 `./configure`——本项目没有构建配置步骤。源码树：

```
lddtree-1.27/
├── lddtree.sh        # 产品本体（POSIX shell，394 行原文）
├── Makefile          # check（上游：kyua）/ lint 目标
├── tests/
│   ├── lddtree_test  # 13 个 ATF 用例
│   ├── test_env.sh   # ATF 用例注册辅助
│   └── testdata/x86_64/…   # 解析用测试数据（含 4 个 hello 二进制）
├── README.md
└── .github/workflows/test.yaml   # 上游 CI：alpine + debian 容器，装了 kyua/atf-sh
```

依赖声明（`conanfile.py`）：

```python
def requirements(self):
    self.requires("binutils/2.46.0")      # 运行时：objdump + readelf

def build_requirements(self):
    self.tool_requires("bmake/20200710")  # 构建期：提供 make
```

### 3. 编译

```bash
$ conan create archives/l/lddtree/1.27 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

**编译耗时**: 约 40 秒（无编译动作；主要耗时在源码下载与 13 个测试用例执行）。

`build()` 实际动作：

1. `apply_conandata_patches()` 应用 2 个补丁（见下）。
2. `sh -n lddtree.sh` —— 语法检查。
3. 探测 ELF 后端（本平台 → `binutils`）。
4. `make -r check` —— 运行上游 13 个测试用例，完整输出回显进日志。
5. 校验汇总行：退出码、用例级（13/13）、断言级（21/0）任一不合格即抛异常。

**编译警告/错误**：

```
lddtree/1.27:   bmake: no system rules (sys.mk).      # 首次尝试，见「问题2」
```

### 4. 安装

```bash
# conanfile.py package() 等价动作
install -D -m 755 lddtree.sh        <pkg>/bin/lddtree.sh
install    -D      README.md        <pkg>/doc/README.md
install    -D      COPYING*         <pkg>/licenses/…
```

**安装文件列表**（包内）：

```
bin/lddtree.sh          11 KB   ← 唯一可执行产物
doc/README.md          2.9 KB
```

## 遇到的问题

### 问题1: 外部 GNU `getopt` 缺失导致所有选项解析失败

**现象**：

```
$ sh lddtree.sh -V
lddtree.sh: invalid option -- 'V'     （或输出 usage 并 exit 1）
```

**原因分析**：上游第 334 行调用 `getopt -n "$argv0" -o "ahlR:Vx" -l … -- "$@"`。
本平台 CI worker 的 PATH 为 `/data/app/bin:/system/bin:/system/sbin:/vendor/bin`，
其中 `/system/bin` 是 toybox，**无 `getopt`**；制品仓也无 util-linux，无法用
`tool_requires` 补齐。

**解决方案**：

```bash
patches/0001-portable-option-parsing.patch      # 73 行，仅改 lddtree.sh
```

以纯 POSIX shell 手工解析替换之，保持全部可观测行为。

### 问题2: 制品仓 bmake 报 `no system rules (sys.mk)`

**现象**：

```
lddtree/1.27:   bmake: no system rules (sys.mk).
lddtree/1.27:   bmake: stopped in /…/b
ERROR: … ConanException: upstream test suite not fully green (make check exit 2)
```

**原因分析**：制品仓 bmake 的 `sys.mk` 位于 `<pkg>/share/mk/sys.mk`，而 bmake
默认不在该目录搜索系统规则文件，因此在读取项目 Makefile 之前就中止。

**解决方案**：

```python
subprocess.run(f'"{make_exe}" -r check', …)   # -r = 禁用内建规则
```

lddtree 的 `Makefile` 显式声明了全部规则与变量，`-r` 不改变其语义；
且 `-r` 同样被 GNU make 接受，故此写法可移植（`make` 与 `bmake` 皆可）。

### 问题3: `BadZipFile: File is not a zip file`

**现象**：

```
lddtree/1.27: Uncompressing v1.27 to .
ERROR: lddtree/1.27: Error in source() method, line 81
	get(self, **self.conan_data["sources"], strip_root=True)
	BadZipFile: File is not a zip file
```

**原因分析**：源码 URL 为 `https://codeload.github.com/ncopa/lddtree/tar.gz/refs/tags/v1.27`，
以**裸 tag** 结尾；Conan 按文件名后缀选择解压器，无 `.tar.gz` 后缀时按 zip 处理。

**解决方案**：改用 `https://github.com/ncopa/lddtree/archive/refs/tags/v1.27.tar.gz`
（sha256 与 codeload 形式完全一致，实测两者均返回 2178596 字节、
`f24b1965…`）。

### 问题4: 运行时无 ELF 解析后端

**现象**：

```
$ lddtree.sh /bin/sh
lddtree.sh: This tool needs either scanelf or binutils (objdump and readelf)
```

**原因分析**：lddtree 自身不解析 ELF，必须外部后端；本平台无 `scanelf`
（pax-utils 未适配），CI worker PATH 中亦无 `objdump`/`readelf`。

**解决方案**：把 `binutils/2.46.0` 声明为**运行时依赖**（`requires` 而非
`tool_requires`）——其 `runenv_info` 会把 `objdump`/`readelf` 注入 PATH，
使 `conan install lddtree/1.27` 直接得到可用工具。

### 问题5: CI L4 门禁误报「危险函数」

**现象**：

```
[warn] L4: Dangerous functions found in patches:
archives/l/lddtree/1.27/patches/0002-self-contained-test-runner.patch
```

**原因分析**：门禁 `grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/` 未加
词首边界，命中的是补丁注释里普通英文词 `targets` 中的子串 `gets`（第 38 行）。
本项目为纯 shell，补丁中不存在任何 C 危险函数调用。

**解决方案**：无需改动（误报、非阻塞 `L4_RESULT=warn`），如实登记。

## 验证测试

### 上游测试套件（真实执行 13 个用例）

```bash
$ make -r check
sh tools/atf-sh-mini tests/lddtree_test
lddtree_usage                    PASS
lddtree_version                  PASS
lddtree_sh                       PASS
lddtree_sh_list                  PASS
lddtree_sh_all                   PASS
lddtree_sh_debug                 PASS
lddtree_sh_missing_scanelf       PASS
lddtree_root                     PASS
lddtree_no_auto_root             PASS
lddtree_no_auto_root_list        PASS
lddtree_ldso_conf                PASS
lddtree_ld_musl_path_conf        PASS
lddtree_rpath_origin_lib         PASS

13 tests, 13 passed, 0 failed, 0 skipped
ASSERTIONS: total=21 failures=0
```

### 基本功能验证

```bash
$ lddtree.sh /bin/sh
sh => /bin/sh (interpreter => /lib/ld-musl-aarch64.so.1)
    libc.so => /system/lib64/libc.so

$ lddtree.sh -l /bin/sh
/bin/sh
/lib/ld-musl-aarch64.so.1
/system/lib64/libc.so

$ lddtree.sh -V
lddtree-1.27
```

### 本地 CI 模拟

```bash
$ CI_PACKAGES=archives/l/lddtree/1.27 zsh ci/conan/build_and_test.sh
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: lddtree.sh --version OK
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
  Pass rate: 100.0% (1/1)
```

## 总结

1. **纯 shell 项目**：本包没有编译步骤，"编译成功"的实质含义是
   `sh -n` 语法检查 + 上游测试套件全绿 + 消费者测试全绿。
2. **平台差异集中在两处外部命令依赖**：`getopt`（选项解析）与
   `kyua`/`atf-sh`（测试驱动）。两者都用**不削弱语义**的方式解决：
   前者替换为等价 POSIX 实现，后者新增自带 ATF 兼容层而**不动上游测试文件**。
3. **运行时后端依赖必须显式声明**：`scanelf` 不可得时，`binutils` 的
   `objdump`/`readelf` 是唯一后端，声明为 `requires` 才能让最终用户拿到可用工具。
4. **可复用的坑**：
   - Conan 源码 URL 必须以 `.tar.gz` 结尾，否则 `BadZipFile`；
   - 制品仓 bmake 需 `-r`，否则 `no system rules (sys.mk)`；
   - CI 的 `build_and_test.sh` 会把 conandata.yml 的 URL 改写成
     gh-proxy 前缀列表，**提交前必须确认恢复为官方单一 URL**（PF7 硬闸）。
