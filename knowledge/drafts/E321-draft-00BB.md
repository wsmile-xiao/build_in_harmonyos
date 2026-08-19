# E321 — Raw makefile Conan 配方的三个通用陷阱

## 错误特征

Raw makefile（非 autotools/cmake/meson 生成 Makefile）软件适配 Conan 时，
连续遇到三个阻塞错误：

```
# 陷阱1: source 阶段
conan.errors.ConanException: ...
  File ".../unzip.py", line ..., in unzip
    raise ConanException("BadZipFile: File is not a zip file")
BadZipFile: File is not a zip file

# 陷阱2: build 阶段
AttributeError: 'str' object has no attribute 'get'
  # 或 KeyError: 'c' — 取决于 conf.get 的返回类型

# 陷阱3: build 阶段
make: *** No targets specified.  No makefile found.  Stop.
```

## 触发条件

- 构建系统: **raw makefile**（手写 POSIX Makefile，无 configure/cmake/meson 生成）
- 阶段: source（陷阱1）、build（陷阱2、3）
- 适用: 从 GitHub codeload 下载源码、在 OHOS 交叉编译环境用 profile
  指定编译器的单文件/小型 C 程序。典型: endlessh 1.1。
- 不适用: autotools/cmake/meson 构建系统（它们有各自的 Makefile 生成
  和编译器获取机制，不受这三个陷阱影响）。

## 根因分析

### 陷阱1: BadZipFile — Conan get() 编码器误选

Conan `tools.files.get()` 通过 **URL 末段文件名**推断压缩格式。GitHub
codeload URL 形如 `https://codeload.github.com/owner/repo/tar.gz/refs/tags/1.1`，
末段是 tag 名 `1.1`（无 `.tar.gz` 扩展名）。Conan 把文件存为 `1.1`，
默认按 zip 解码器解压，但实际是 tar.gz 文件，导致 `BadZipFile`。

`conandata.yml` 中虽声明了正确 URL，但 `get()` **不读** conandata 的
`tar_format` 字段做格式提示。

### 陷阱2: compiler_executables 字典获取失败

OHOS profile 中 `tools.build:compiler_executables` 配置为**字典**格式：
```ini
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
```
直接用 `self.conf.get("tools.build:compiler_executables")` 不带类型检查，
会返回字符串或报错，后续 `.get("c")` 失败（`AttributeError: 'str' object
has no attribute 'get'`）。这是因为 Conan conf 的值类型推断不明确。

### 陷阱3: make 默认 cwd 错误

`self.run("make ...")` 默认在 `build_folder` 执行。但 raw makefile 的
`Makefile` 位于 `source_folder`（Conan 的 `basic_layout` 将源码解压到
source_folder，build_folder 是空的或用于生成产物）。autotools/cmake 会
把 Makefile 生成到 build_folder，但 raw makefile 不会，导致 make 找不到
Makefile 报 `No targets specified. No makefile found.`。

## 解决方案

### 推荐方案：raw-makefile-conan-recipe-pattern 三要素

三个陷阱必须同时修复，缺一不可：

```python
# 陷阱1修复: get() 显式传 filename 带扩展名
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True,
        filename="endlessh-1.1.tar.gz")  # ← 关键: 显式扩展名

# 陷阱2修复: check_type=dict 整体获取字典
def build(self):
    comp_execs = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict)  # ← 关键: dict
    cc = comp_execs.get("c") or "clang"

    # 陷阱3修复: cwd=source_folder
    self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)  # ← 关键: cwd
```

### 回退方案

若 Conan 版本过旧不支持 `check_type` 参数，可用 `os.environ.get("CC")`，
但 **R33 要求从 Conan conf 获取而非环境变量**，故不推荐。

### 禁止做法

- ❌ `get(self, **self.conan_data["sources"], strip_root=True)` 不传 filename
  （codeload URL 末段无扩展名时必然 BadZipFile）
- ❌ `self.conf.get("tools.build:compiler_executables")` 不加 `check_type=dict`
  （字典值被当字符串处理，后续 `.get()` 失败）
- ❌ `self.run("make ...")` 不指定 `cwd`
  （raw makefile 的 Makefile 在 source_folder，build_folder 找不到）
- ❌ `os.environ.get("CC")` 获取编译器
  （违反 R33: 必须从 Conan conf 获取，不用环境变量）
- ❌ OHOS 平台用 `make install` 安装
  （OHOS 无 `install` coreutils 命令，改用 Conan `copy()`）

## 验证

```bash
# 三个陷阱修复后验证
python3 scripts/ohc-run.py conan-verify endlessh 1.1
# G1 PASS, G2 PASS (conan create + test_package 通过)

# 确认 conanfile.py 包含三个修复
grep "filename=" archives/e/endlessh/1.1/conanfile.py
grep "check_type=dict" archives/e/endlessh/1.1/conanfile.py
grep "cwd=self.source_folder" archives/e/endlessh/1.1/conanfile.py

# 确认无 BadZipFile / makefile not found 错误
grep -E "BadZipFile|No makefile found" archives/e/endlessh/1.1/reports/conan-create.log
# 空输出即已修复
```

## 交付证据

- 软件: endlessh 1.1
- 日期: 2026-08-19
- conan-verify: G1 PASS, G2 PASS, G3 PASS
- test_package: endlessh -h exit 0
- 二进制安全: NX/PIE/Full RELRO 合格

## 关联条目

- 相关: E321-conan-get-url-no-extension-badzipfile（陷阱1 的单条目版，
  本条目合并了三个陷阱为 raw makefile 通用模式）
