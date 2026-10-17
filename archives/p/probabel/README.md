# probabel OpenHarmony 编译记录

ProbABEL 是 GWAS（全基因组关联分析）命令行工具集：palinear（线性回归）、
palogist（逻辑回归）、pacoxph（Cox 比例风险）三个分析二进制，经 `probabel`
perl 包装器统一调用，支持按染色体分块的剂量文件并行分析。统计核心基于
上游捆绑的 Eigen 3.2.1 模板库，无外部依赖。

本目录当前包含 0.5.0 首适版本（GitHub 官方 tag tarball）：

- 分析工具 `bin/palinear`、`bin/palogist`、`bin/pacoxph`
- 包装器 `bin/probabel`（perl）与别名 `bin/probabel.pl`
  （相对符号链接，`package()` 内由配方改写，保证换 CONAN_HOME/换机可解析）
- 无头文件/库交付：`cpp_info` 仅声明 bindirs（工具型包）

OHOS 适配要点（详见 0.5.0/notes.md）：

1. tarball 只带 configure.ac，构建期先 `autoreconf -fi`；
2. configure 的 `umask 077` 在 HMDFS 上移除（E011/E114）；
3. configure/make/install 以 `env -u CONFIG_SHELL SHELL=/bin/sh` 路由
   （E386）；上游测试套件按上游自身写法以 hnp bash 驱动 `make -j1 check`，
   checks/*.sh 的 fd-3 惯用法改写为等价重定向；
4. `src/probabel` 包装器 shebang 改 hnp perl；`VAR+=` 非 POSIX 追加改写为
   POSIX 等价（0001）；`static const double` 类内初值化改 `constexpr`（0002）；
5. bundled Eigen 3.2.1 依赖 C++17 已删除的 `std::binder1st/std::bind2nd`，
   统一 `-std=gnu++14`；
6. 上游 `checks/` 套件 11 项 shell 测试在配方 build() 内真实执行（11/11 PASS），
   R 参照测试（R-tests/，3 项）需 R 解释器，OHOS 环境无 R 未注册未执行
   （上游 HAVE_R 条件接线，非本次适配造成）；
7. `probabel.pl` 安装别名不可重定位缺陷（构建期绝对路径烙进链接目标）的
   根因与修法沉淀为知识草稿
   `DRAFT-probabel-0.5.0-destdir-baked-symlink-alias-non-relocatable`。
