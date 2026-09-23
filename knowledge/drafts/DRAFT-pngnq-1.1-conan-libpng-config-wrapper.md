# DRAFT-pngnq-1.1-conan-libpng-config-wrapper

## 场景

老 autotools 软件（pngnq 1.1, 2010）在 `src/Makefile.am` 中用反引号硬编码
`libpng-config --I_opts` / `--ldflags` 获取 flags；conan 依赖包内的
libpng-config 因 relocatable 布局 prefix 为空，输出不可用。

## 根因

- Makefile.am 反引号调用不经过 pkg-config，AutotoolsToolchain 不注入依赖 -I/-L
- conan 包内 libpng-config 的 prefix="/"，输出 `-I//include`
- configure 的 `PKG_CHECK_MODULES([PNG], [libpng])` 需要 PkgConfigDeps 生成的 .pc

## 方案（pngnq 1.1 实证）

1. `generators = "PkgConfigDeps"` — 满足 configure 的 pkg-config 检查
2. build() 内生成 POSIX sh wrapper（`--version/--I_opts/--L_opts/--ldflags/--static`），
   路径取自 `self.dependencies["libpng"].package_folder`
3. `Environment().append("PATH", wrapper_dir)` 前置 PATH（`define_path` 是追加语义）
4. 两个坑：
   - 模板含 shell `${prefix}` 时禁用 `str.format()`（KeyError）→ 用 `%` 格式化
   - wrapper 内 shell 变量避开 `version=` 字面量（CI 正则 `^\s*version\s*=` 会误提取
     到 `%s`，导致 L0m "版本目录与 conanfile version 不一致"误报）→ 改名 `png_version`

## 验证

conan create 八门禁全绿；test_package 8/8（真实量化 + pngcomp）；pngnq -V 报告
libpng 1.6.39 / zlib 1.3.1。
