# E322 — AutotoolsDeps 导出 LIBS，使 autoconf 最早的运行探测就链接整条依赖闭包

## 错误特征

三元组已经识别正确，却在下一行就失败：

```
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking whether the C compiler works... yes
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
If you meant to cross compile, use `--host'.
```

`config.log` 中该探测的链接命令里出现了全部依赖：

```
clang -o conftest -O3 -I<pkg>/include ... conftest.c -lXrender -lX11 -lxcb \
      -lfontconfig -lXdmcp -lXau -lfreetype -lxml2 -lm
./conftest
Error loading shared library libfontconfig.so.1: (needed by ./conftest)   $? = 127
```

## 触发条件

- 构建系统: autotools（Conan `AutotoolsDeps`）
- 阶段: configure 最早期（`AC_PROG_CC` 的交叉编译判定）
- 平台: os=OHOS 且依赖以共享库交付

## 根因分析

`AutotoolsDeps` 会把依赖闭包写进 `LIBS`/`CPPFLAGS`/`LDFLAGS` 等环境变量。
autoconf 的 `AC_PROG_CC` 为了判断"是否需要交叉编译"，会编译**并运行**一个只含
空 `main` 的程序——但它沿用了环境里的 `LIBS`，于是这个本应零依赖的探测
被链接上整条共享依赖闭包。只要闭包中有任一库在本机不可加载（签名无效见 E321、
别名不可解析见 E257），失败就提前暴露在 configure 阶段，表现为 rc=77
`cannot run C compiled programs`，很容易被误判成编译器坏了或三元组不对。

## 解决方案

### 推荐方案

1. **先读 `config.log`**，取出该探测的完整命令与第一条真实错误，
   再决定修哪一层——不要根据 configure 最后一行猜。
2. 按第一条错误归类：`No such file` → 搜索路径；`Permission denied` → 签名（E321）；
   名字存在但 `(needed by ...)` 失败 → 符号链接别名/优先级（E257）。
3. 在任务私有构建目录内修好可加载性（实体化 + 重签名视图），让探测**真实通过**。

### 禁止做法

- ❌ 加 `--host=<triplet>`：让 `cross_compiling=yes` 直接**跳过**运行探测，
  R1 明令禁止，且 `AC_RUN_IFELSE` 全被跳过会产出不符实
- ❌ 预设 `ac_cv_prog_cc_works=yes` / `cross_compiling=no` 缓存变量伪造结果
- ❌ 空实现或无条件成功的探测结果替代真实检测
- ❌ 因为"运行不起来"就把依赖改成静态链接来掩盖运行环境问题

## 验证

```bash
# 还原探测命令并单独运行，确认修好后 rc=0
grep -B2 -A8 'cannot run C compiled programs' "$B/config.log"
cd "$B" && <复现编译命令> && env -u LD_LIBRARY_PATH ./conftest; echo $?
```

## 关联条目

- 相关: E257（加载器搜索路径语义）、E321（签名有效性）、E007/E072（三元组）
- 来源: libxft 2.3.8 适配，2026-08-28，conan create r2/r3/r4 实测
