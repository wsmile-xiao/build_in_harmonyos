# inheritenv 0.2 适配笔记

## 上游与产物

- 上游发行包 `inheritenv-0.2.tar.gz`（GitHub tag 0.2，Steve Purcell）：
  GNU Emacs Lisp 包，解决 Emacs 库在临时缓冲区运行后台进程时不继承调用
  缓冲区局部环境变量（`process-environment`/`exec-path`）的陷阱。提供
  `inheritenv` 宏（库作者包装用）与 `inheritenv-add-advice` 宏（用户改造
  命令用）。sha256=82ced13a...7b2b 实测（github.com 归档 URL 与 codeload
  字节一致）。
- 发行内容：`inheritenv.el`（87 行，核心）+ `inheritenv-tests.el`（38 行，
  ERT 测试）+ README.md + Makefile + GitHub CI 配置。
- 许可证：GPL-3.0-or-later（仓库无独立 LICENSE 文件，GPL 声明在 .el
  文件头注释中）。
- **任务平台标签为 C++，实为 Emacs Lisp 包**：发行包内无任何 C/C++ 源码。
  按已合并的 ace-link 纯数据包先例适配；如需确认可与小助手核对。
- 上游要求 Emacs ≥ 24.4（Package-Requires 头）。tag 0.1 与 0.2 均存在，
  0.2 为最新。

## OHOS 适配

纯 Elisp 数据包（ace-link 范式），无编译无链接：

- `build()` 仅做防漂移清单校验：两 .el 文件在位且行数落在实测区间
  （87/38 行 ± 容差）、README.md 在位；
- `package()` 把 .el 文件与 README 装到 `lib/site-lisp/`，Emacs 经
  load-path 加载；字节编译留给 Emacs 运行时；
- 上游 Makefile 的 compile/package-lint/test 目标均需 Emacs 运行时
  （package-lint 还需 MELPA 联网），配方构建期一律不执行（R1）；
- `cpp_info.includedirs = ["lib/site-lisp"]`，无库无 bin。

## 测试口径

上游有测试套件（R51 已清点）：`inheritenv-tests.el` 含 1 个 ERT 用例
（inheritenv-test-propagation，3 个 should 断言：默认临时缓冲区不继承 /
`inheritenv` 宏内继承 / `inheritenv-add-advice` 改造后继承），GitHub Actions
CI 矩阵覆盖 Emacs 24.4–28.2。适配后消费者探针（test_inheritenv.py）：

1. 两 .el 文件在位且非空；
2. inheritenv.el 六个发行标记（文件头、Version 0.2、provide、两个
   defmacro、GPL 许可头）；
3. tests 文件 ERT 用例标记；
4. 宿主有 emacs 时**原样执行上游 ERT 测试命令**（`emacs -Q --batch -L
   <pkg>/lib/site-lisp -l inheritenv.el -l inheritenv-tests.el -f
   ert-run-tests-batch-and-exit`，即上游 Makefile test 目标去掉需联网的
   package-lint 部分）并检查退出码；无 emacs 则跳过并注明。

## 参考

- GitHub: https://github.com/purcell/inheritenv
- MELPA: https://melpa.org/#/inheritenv

## 真机验证（2026-09-25，HarmonyOS PC）

`python3 scripts/ohc-run.py conan-verify inheritenv 0.2` 真机实跑全绿
（G0-G4 PASS；L2/L4/L5 为产物二进制相关框架门禁，纯数据包无产物按框架跳过），
exit 0。关键证据：

- conan create 干净构建成功：`Package 'fc3eeb021243959114a0318489539cad6d087e28' created`，
  编译环境 settings `os=OHOS os.version=6.0 arch=armv8`（真机鸿蒙环境实证）；
- 构建期防漂移校验全过：inheritenv.el 87 行、inheritenv-tests.el 38 行，
  均落在实测区间；
- package()：2 个 .el 文件（inheritenv.el / inheritenv-tests.el）+ README.md
  装入 lib/site-lisp；
- 探针 test_inheritenv.py 真机输出：3 组静态断言全过；宿主无 emacs，
  上游 ERT 套件按设计跳过并显式注明（`NOTE: emacs not found on this host;
  upstream ERT suite skipped`），探针 PASS。

产物 revision：fc3eeb021243959114a0318489539cad6d087e28；
conan create 完整日志与 8 门禁报告见 reports/。

## 真机复验（2026-09-25，L0p 修复后）

CI 首轮 L0p 门禁 FAIL：`settings = "os", "arch"` 缺 compiler/build_type
（OHOS profile 要求全部四项，ace-link 老写法已不通过）。修复=settings 四项
+ `package_id` 清空（纯数据包无编译产物，避免 compiler/build_type 造成无意义
包分裂，header-only 模板范式）。修复版真机复验全绿（G0-G4 PASS，L2/L4/L5
按框架跳过），exit 0：

- conan create 干净构建成功：Package `da39a3ee5e6b4b0d3255bfef95601890afd80709`
  created（package_id 清空后的固定空 ID），配方 revision
  `#8e31a0cae29360745884db002a600278`；
- 探针同款 3/3 全过：`PASS: inheritenv.el installed with 0.2 markers
  (ERT suite skipped: no emacs)`。

## CI 下载源说明

conandata 下载 URL 为官方原始 github.com tag 归档（review-memory R39 第 13 条：
只写官方原始 URL，不手动加镜像前缀——CI 会为 GitHub URL 自动注入镜像
fallback）。sha256 以官方归档实测值为准（github.com 归档与 codeload 字节一致，
本地已比对）。曾短暂用 ghproxy.net 前缀（误判 CI 网络），/ai review 指出违反
R39 后已回退（commit f038bb43 之后的修复提交）。真机验证期间 E017 会往
github.com URL 注入失效镜像，故真机下载走本地 http.server 镜像（绕过 E017），
URL 仅在设备 scratch 态，不进仓库。
