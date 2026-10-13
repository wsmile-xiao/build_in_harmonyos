# Autoconf 探测结果与手写链接线分裂：科学计算程序“补齐 FortranRuntime 后能链接”仍可能是双 BLAS/LAPACK 后端

> 状态：DRAFT（路径 B 知识库扩展候选）｜来源：phyx/1.3.2 HarmonyOS PC 适配｜日期：2026-10-11
> 候选编号：E14851｜机器可读层：`E14851-draft-C5E9.kv`

## 结论

科学计算程序的 `configure` 成功并不保证最终目标使用了被探测到的数学库。当
`configure.ac` 通过 `AC_CHECK_LIB` / `AC_SEARCH_LIBS` 形成全局 `LIBS`，而手写
`Makefile.in` 又维护一条不含 `@LIBS@` 的 `CPP_LIBS=-llapack -lblas ...` 时，探测
与交付已是两个互不约束的依赖图。

在 HarmonyOS 上，给 reference LAPACK/BLAS 机械追加 `FortranRuntime` 可以把链接
错误消掉，却可能把 reference 的 `dgemm_`、`dgesv_`、`dgetrf_` 静态嵌入程序，
同时程序又经 `libarmadillo.so` 装载 `libopenblas.so.0`。此时进程中出现两套同名
Fortran ABI 数学符号；“链接成功”和一次冒烟输出都不足以证明后端唯一。

## phyx 的三臂实证

### A：上游原始链接线失败

上游 `src/configure.ac` 已有：

```m4
AC_CHECK_LIB(nlopt,nlopt_version,...)
AC_SEARCH_LIBS([wrapper_sgesv_], [armadillo], [have_arma=yes])
```

但 `src/Makefile.in` 未消费 `@LIBS@`，另行硬编码：

```make
CPP_LIBS = -llapack -lblas -lpthread -lm
CPP_LIBS += -lnlopt
CPP_LIBS += -larmadillo
```

对 OHOS aarch64 重目标链接时，reference LAPACK/BLAS 拉入 Flang 实现并失败于
`_FortranA*` 未定义符号。根因不是“少两个普通系统库”，而是最终链接线绕开了
configure 已识别的 Armadillo 提供者。

真机同目标文件对照的退出码为 2，实际错误包括
`_FortranACharacterCompareScalar1`、`_FortranAioBeginExternalFormattedOutput`、
`_FortranAioOutputAscii` 与 `_FortranAStopStatement`。

### B：追加 FortranRuntime 后假修复

在原链接线尾部追加 `-lFortranRuntime -lFortranDecimal` 后，链接返回 0；但制品
审查同时得到：

```text
llvm-nm --defined-only <bin>  → dgemm_ / dgesv_ / dgetrf_ 为已定义
llvm-readelf -d <bin>         → NEEDED libarmadillo.so
libarmadillo.so               → NEEDED libopenblas.so.0
```

即 reference 实现已静态进入可执行文件，OpenBLAS 又在动态闭包中。Fortran runtime
只是让错误消失，没有恢复“一个 ABI 符号只有一个后端”的包管理契约。

该反例不是推测：同一组目标文件追加两个 runtime 后退出码为 0，`llvm-nm` 实测
三项代表符号均为 `T`，而 `llvm-readelf` 同时确认上述两层动态闭包。

### C：保留 Autoconf 的提供者结论

修复只做两件事：

1. 配方只向 `CFLAGS/CXXFLAGS/LDFLAGS` 注入依赖的 `-I/-L` 搜索目录，不预填完整
   `LIBS`；因此 `AC_SEARCH_LIBS(wrapper_sgesv_, armadillo)` 实际返回
   `-larmadillo`，不会被既有闭包短路为 `none required`。
2. `Makefile.in` 改为 `CPP_LIBS = @LIBS@ -lpthread`，并按 `HNLOPT=Y` 保留
   `-lnlopt`；让 `AC_SEARCH_LIBS` 的数学提供者结论成为重目标唯一链接事实来源。

修复后的重目标通过以下硬门禁：

```bash
llvm-readelf -d pxseqgen | grep -E 'libblas|liblapack|libFortran(Runtime|Decimal)'
# 期望 0 命中

llvm-nm --defined-only pxseqgen | grep -E ' (dgemm_|dgesv_|dgetrf_)$'
# 期望 0 命中
```

三臂原始日志置于仓库外，SHA256 为
`5a20094e3977b9726db529253af8f11453e6dfc859ce833f15da5bf9e5a5c5c5`；提交内的
脱敏命令、退出码和关键输出见 `archives/p/phyx/1.3.2/reports/path-b-evidence.md`。

随后必须运行固定输入的确定性数据测试；phyx 使用官方 `TEST/test.fa` 验证 5 条序列、
长度 20、A/C/G/T 精确计数与 GC=0.55，并运行上游全部 100 项：95 项精确匹配，
另 5 项随机输出比较由上游 runner 明确列为 anticipated failures 且整体成功退出。
这一步防止“后端唯一但计算语义已漂移”的另一种假绿。

## 为什么不能直接使用 AutotoolsDeps

`AutotoolsDeps` 通常是正确模板，但对“宏的返回值稍后被 Makefile 当作提供者事实”
的工程不能无条件套用。它把依赖闭包预装进 `LIBS` 后有两个副作用：

- `AC_SEARCH_LIBS` 发现符号已经可解析，返回 `none required`，`@LIBS@` 不再记录
  具体提供者；
- native configure 的早期“能否运行编译产物”探针也携带这些共享依赖，加载路径
  尚未建立时会报 `cannot run C++ compiled programs`。

这里应只提供搜索路径，让上游探针自己决定库名。这个边界与“遗漏 AutotoolsDeps
导致完全找不到依赖”的既有条目相反，不能互相机械套用。

## 查重与新增差异

| 既有条目（完整 stem/标题） | 重合背景 | 本条新增机制 |
|---|---|---|
| `E566-draft-A26E.kv`（未完成草稿：PkgConfigDeps 引号路径 / `AC_CHECK_LIB` 与 LDADD 分裂） | `AC_CHECK_LIB` 结果未进入真实链接线，但条目仍保留模板空字段，不能直接复用 | 本条提供完整三臂实证，新增多数学提供者、FortranRuntime 假修复及 ELF 双视角门禁 |
| `E577-draft-lcs-flat-ncursesw-probes.kv`（Conan ncurses 平铺布局与 `AC_SEARCH_LIBS none required`） | `AutotoolsDeps` 预填 `LIBS` 会短路探针 | 本条消费点是 `@LIBS@` 与科学计算后端唯一性，不是 ncurses 头/库布局和宏选择 |
| `E667-blaspp-cmake-blas-libraries-passthrough-link-order.kv`（BLAS++/LAPACK++ finder 与静态拓扑序） | reference BLAS/LAPACK 的 Flang runtime 及静态链接顺序 | 本条处理 Autotools 探测/交付分裂，并识别静态 reference 与动态 wrapper 后端共存 |
| `E677-lapackpp-tester-lapacke-via-openblas-transitive-provider.kv`（LAPACKE 经 OpenBLAS 传递提供） | OpenBLAS 可作为传递提供者 | E677 刻意利用静态扫描顺序避免重复定义；本条识别并禁止已经链接成功的双提供者制品 |

检索范围覆盖 `knowledge/graph`、`knowledge/doc`、`knowledge/drafts` 和赛事文档；未找到
把“探测/最终链接分裂 → FortranRuntime 假修复 → 静态符号 + DT_NEEDED 联合审计 →
确定性数据回归”作为完整可复用机制的既有条目。

## 适用与禁止

适用于 Autotools 科学计算应用，以及所有同时存在“可替代实现 + wrapper 库 + 手写
链接变量”的工程。迁移时应先比较探测宏输出变量与每个真实目标的链接变量，再做
ELF/符号审查。

- 禁止把 `-lFortranRuntime -lFortranDecimal` 当作最终修复结论；
- 禁止在同一重目标链接线同时保留 reference `-llapack -lblas` 与
  `-larmadillo/-lopenblas`；
- 禁止只看 `DT_NEEDED`：静态实现不会以 NEEDED 出现，必须再查普通符号表；
- 禁止只跑 `--version` 便声明科学计算可用，必须有固定输入与精确结果断言。
