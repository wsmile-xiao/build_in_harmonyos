# E317: autotools Makefile.in install sed 全局替换固化 ${VAR} 引用，需范围限定替换

> **Contributor**: RBA1 | **Status**: DRAFT | **Created**: 2026-08-09
> **Severity**: medium | **Category**: installation|relocatable|autotools

## 错误特征

R 4.5.1 在 HarmonyOS 上以 `--prefix=/` + `DESTDIR` 模式安装，并将包移动到非原路径后运行 R，`R.home("share")` 返回错误路径 `//lib/R/share`，`normalizePath()` 报 `No such file or directory`。具体表现为：

```text
> R.home("share")
[1] "//lib/R/share"
> normalizePath(R.home("share"), mustWork=TRUE)
Error in normalizePath(R.home("share"), mustWork = TRUE) :
  path[1]="//lib/R/share": No such file or directory
```

该错误仅在包被移动到非原路径（moved-r-base）后出现。在原始构建路径下 R 可正常运行，因为 `//lib/R/share` 恰好与原始安装路径一致。

## 触发条件

1. R 4.5.1 在 HarmonyOS 上使用 autotools 构建，configure 阶段设置 `--prefix=/`。
2. `make install DESTDIR=<pkg>` 将 R 安装到 `<pkg>/lib/R/...`。
3. consumer 将包移动到 `moved-r-base` 目录，并屏蔽 Conan cache。
4. 在 moved-r-base 下运行 R，launcher 探测 R_HOME_DIR 并 re-derive 资源目录。
5. `R.home("share")` 调用 `R_SHARE_DIR`，但该变量已被固化为 `//lib/R/share`。
6. `normalizePath()` 对不存在的 `//lib/R/share` 报错。

## 根因分析

R 的 `src/scripts/Makefile.in` 中 install 规则使用 sed 处理 R 脚本中的变量赋值。对 `R_HOME_DIR` 的处理采用范围限定替换 `1,/R_HOME_DIR=/s/\(R_HOME_DIR=\).*/\1<fixed_value>/`，只替换第一个出现的赋值行（即 configure 固化的默认值），保留后续 re-derive 块中的 `R_HOME_DIR="${R_HOME_DIR}"` 变量引用。

然而对 `R_SHARE_DIR`、`R_INCLUDE_DIR`、`R_DOC_DIR` 的处理使用了全局替换 `s/\(VAR=\).*/`（无 `1,/PATTERN=/` 范围限定），导致 re-derive 块中的变量引用也被固化为 configure 编译期值：

```makefile
# Makefile.in install 规则（修复前）
sed -e 's/\(R_SHARE_DIR=\).*/\1${rsharedir}/' \
    -e 's/\(R_INCLUDE_DIR=\).*/\1${rincludedir}/' \
    -e 's/\(R_DOC_DIR=\).*/\1${rdocdir}/' \
    $(srcdir)/R > R
```

re-derive 块中本应保留的 shell 变量引用 `R_SHARE_DIR="${R_HOME_DIR}/share"` 被一并固化为 `R_SHARE_DIR="//lib/R/share"`（`--prefix=/` 时的编译期值）。包移动后该路径不存在。

此问题属于 autotools install 阶段的 sed 替换范围缺陷，不是 R 代码 bug 或运行时能力问题。

## 解决方案（含验证）

### 推荐方案：范围限定 sed 替换（补丁 0009）

补丁 0009 将 `src/scripts/Makefile.in` install 规则中 `R_SHARE_DIR`/`R_INCLUDE_DIR`/`R_DOC_DIR` 的 sed 替换从全局 `s/\(VAR=\).*/` 改为范围限定 `1,/VAR=/s/\(VAR=\).*/`，与 `R_HOME_DIR` 的处理方式对齐：

```makefile
# Makefile.in install 规则（修复后）
sed -e '1,/R_SHARE_DIR=/s/\(R_SHARE_DIR=\).*/\1${rsharedir}/' \
    -e '1,/R_INCLUDE_DIR=/s/\(R_INCLUDE_DIR=\).*/\1${rincludedir}/' \
    -e '1,/R_DOC_DIR=/s/\(R_DOC_DIR=\).*/\1${rdocdir}/' \
    $(srcdir)/R > R
```

关键设计点：

1. **范围限定**：`1,/PATTERN=/` 只替换从文件首行到第一个匹配 `PATTERN=` 的行范围内出现的赋值，即只替换 configure 固化的默认行。
2. **保留 re-derive**：re-derive 块中的 `R_SHARE_DIR="${R_HOME_DIR}/share"` 变量引用不在替换范围内，保持运行时从 `R_HOME_DIR` 重新推导的能力。
3. **对齐 R_HOME_DIR**：`R_HOME_DIR` 已采用 `1,/R_HOME_DIR=/` 范围限定，此补丁使三个资源目录变量与之对齐。
4. **launcher 复合策略**：与 E215（LuaRocks launcher/TMPDIR 可重定位相关条目，属同类 launcher 自定位问题）配合使用——launcher 探测 R_HOME_DIR → re-derive 块从 R_HOME_DIR 推导 R_SHARE_DIR → 范围限定 sed 保留推导逻辑 → CA bundle 复用 R_HOME_DIR 定位 cert。四者共同构成可重定位运行时策略。

### 验证

```bash
# 修复前（包移动后）
cd moved-r-base && R -e 'cat(R.home("share"), "\n")'
# 输出: //lib/R/share

# 修复后
cd moved-r-base && R -e 'cat(R.home("share"), "\n"); cat(normalizePath(R.home("share"), mustWork=TRUE), "\n")'
# 输出: <moved-r-base>/lib/R/share
#       <moved-r-base>/lib/R/share
```

moved-r-base 场景下 `R.home("share")` 返回正确的相对推导路径，`normalizePath()` 成功解析。Round 16 retry-03 完整 CI exit 0。

## 互引说明

- **similar_to E005**: E005 是 Conan 包可重定位运行时的通用策略；E317 是该策略在 autotools install sed 替换环节的具体实现——范围限定替换保留 re-derive 块中的变量引用。
- **similar_to E078**: E078 是 R install 阶段 `R_HOME_DIR` 的范围限定 sed 处理；E317 是将同一模式扩展到 `R_SHARE_DIR`/`R_INCLUDE_DIR`/`R_DOC_DIR` 三个资源目录变量。
- **similar_to E176**: E176 是动态链接器拒绝加载 ICU stubdata；E317 是 install sed 全局替换固化变量引用。两者均为平台适配中发现的构建/安装链路缺陷，修复策略均为范围限定或能力探测。
- **similar_to E215**: E215 是 LuaRocks launcher/TMPDIR 可重定位相关条目；E317 是 autotools install sed 范围限定补丁，二者分属不同构建系统的可重定位问题；E317 的 launcher 配合策略仅指 r-base 自身 launcher 探测（patch 0006），与 E215 属同类问题但不同库不同轴。
- 与 E243（Rprof ITIMER）、E244（时区）、E245（OpenBLAS SONAME）属同一 r-base 4.5.1 适配批次（Round 5-16），但解决的问题轴不同。
