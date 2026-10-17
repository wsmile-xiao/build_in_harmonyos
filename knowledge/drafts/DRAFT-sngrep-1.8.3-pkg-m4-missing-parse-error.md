# DRAFT-sngrep-1.8.3-pkg-m4-missing-parse-error

## 症状
工具链缺 pkg.m4（`aclocal --print-ac-dir` 下无 pkg.m4）的项目 autoreconf 自举后，运行 `./configure` 直接抛 shell 解析错误，例如：

```
./configure[7752]: syntax error: unexpected 'LIBGCRYPT,'
```

与经验汇总 §970 记录的 `syntax error near unexpected token GLIBS,` 同症状。**特殊性**：即使把对应特性 `--without-gnutls` 整体禁用，错误依旧——它是解析期错误，与运行时分支无关。

## 根因
- autoreconf 展开时，`m4_ifdef([PKG_CHECK_MODULES], [ … ], [ else-分支 ])` **守卫内**的调用在宏缺失时正常回落到 else 分支（纯 `AC_CHECK_LIB` 探测），所以大多数项目"看起来没坏"；
- 但 sngrep 的 configure.ac 把 `PKG_CHECK_MODULES([LIBGCRYPT], [libgcrypt])` 用在了**任何 m4_ifdef 守卫之外**（上游默认大家都有 pkg.m4）。宏未定义时 m4 不认识它，原样留进生成的 configure；
- 该行作为 shell 语句 `PKG_CHECK_MODULES(LIBGCRYPT, libgcrypt)` 语法非法 → 整个 configure 解析失败。

判别方法：`grep -n '^\s*PKG_CHECK' configure` 找裸行；`bash -n configure` 复现解析失败。

## 解法（两条，按需选）
1. **标准解法（= §970）**：`cp /data/service/hnp/pkg-config.org/*/share/aclocal/pkg.m4 <项目>/m4/` 再 `autoreconf -fi`。保留 pkg-config 探测的 -I/-L/版本约束注入，适合确实要启用该特性的项目。
2. **去 pkg-config 化（本条新增）**：把该探测段改写为纯 `AC_CHECK_LIB`/`AC_CHECK_HEADER`，从根上不依赖 pkg.m4。**代价（E2186 同类坑）**：`AC_CHECK_LIB` 不注入 `-I` 与版本约束——仅当对应特性在本包已整体禁用（分支运行时不进入）或依赖路径已由其它方式（conan CPPFLAGS 注入等）提供时才安全；启用者必须自行补 `CPPFLAGS`/`PKG_CONFIG_PATH` 并在 notes 里写明。

sngrep 1.8.3 采用解法 2（gnutls 特性整体 `--without-gnutls` 禁用，libgcrypt 探测分支运行时不进入），以 `patches/0003-configure.ac.patch` 落地，`bash -n` 校验 + conan create 全链 + 上游 make check 11/11 验证。

## 适用范围 / 反例 / 风险
- 适用：所有在无 pkg.m4 工具链上自举、且 configure.ac 存在未守卫 PKG_CHECK_* 调用的项目。
- 反例：守卫内的调用（m4_ifdef 包裹）不需要处理——它们本来就能正确回落。
- 风险：解法 2 若用于"要启用特性"的场景且不补 -I，会出现 E2186（探绿但 make 首错 header not found）。
- 关联：§970（标准解法）、E089（不同签名）、E2186（-I 注入反例）、E011/E114/E386/E002（同包自举链的其余坑，见 notes.md）。
