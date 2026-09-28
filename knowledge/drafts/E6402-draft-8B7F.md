# E6402 — NLS 已关闭时，旧 intltool 宏仍误检 XML::Parser

## 场景与现象

含 `IT_PROG_INTLTOOL` 的旧 Autotools 项目在 `--disable-nls` 后，`configure` 仍报 `XML::Parser perl module is required for intltool`。补装预构建 Perl 模块未必有效：若其 XS 扩展与设备 Perl ABI 不一致，实际加载会报 `PL_markstack_ptr: symbol not found`。pslib 0.4.8 在 OHOS 上依次复现了缺 intltool、缺 gettext、缺 XML::Parser 和 XS ABI 不兼容四个配置阶段失败，四次失败各有独立事务与日志。

## 精确根因与判断

生成的 `configure` 先将 `--disable-nls` 解析成 `USE_NLS=no`，但 `IT_PROG_INTLTOOL` 展开的 XML::Parser 检查使用恒真守卫，未按 NLS 状态区分。`po/Makefile` 的 `all-no` 确实不编译翻译目录，却不能据此删除所有 i18n 工具：本次 `make check` 仍进入 `po` 并执行 `intltool-update --pot` 和 `-m`。因此 XML 模块检查是冗余的，真实 intltool/gettext 工具并非完全冗余。

## 可复用修复

1. 确认调用使用 `--disable-nls`，`po` 的 `all-no` 不产生需要 XML 合并的翻译目标，且没有其他目标调用 `intltool-merge -x`。
2. 对目标版本生成的 `configure` 做精确一次替换：把 `if test "x" != "xno-xml"; then` 改为 `if test "$USE_NLS" = "yes"; then`。出现次数不为一时失败退出，不能做模糊全局替换。启用 NLS 时仍保留原检查。
3. 保留真实的 intltool 与 gettext 构建工具。若制品包脚本 shebang 指向已消失的 Perl，优先在任务构建目录生成调用当前 Perl 的包装器，勿修改共享包缓存或目标机全局工具。
4. 执行完整 `make check` 与安装后 API 消费者测试，并验证输入、日志、远端回执 SHA-256。

## 本次证据

- `pslib/0.4.8` 的失败日志 SHA-256：缺 intltool `8b262e03d6fac99c0b0b48ee3b6cc65312798a15620c5f620ba9b142d861793a`；缺 gettext `f4d3485ceeb29668dae8806571ff42fe9bc30c51c0d0b157fc28d5ca6c8b0723`；缺 XML::Parser `ce42967f2c725ee36c0ef139f1785c8cf09e0f555912e9d5ebee54c539dcc50b`；ABI 错误诊断对应事务日志 `98ea3e72ee11c7d9cbcb785546d15bb85a446fac44738ffceef9f033c1aecb80`。
- 修复后目标机事务 `pslib-w3-20260926T024600Z` 完成 12/12 回执，构建日志 SHA-256 `84af84194ee531e6db199fcf2cca9baa96f6d1760113dd881f6e342cfb1cef69`。`png_read_image`、`jpeg_read_header` 检测均为 yes；`make check -j1` 全部退出 0；源码无注册的上游测试用例（0/0），安装后 `test_package` 一项生成并检查内存 PostScript 文档（1/1 PASS）。

## 适用边界与查重差异

仅适用于可关闭 NLS、且禁用后不运行 XML 合并的旧 Autotools 项目。若必须翻译 XML/UI 文件，不能跳过 XML::Parser；应针对当前 Perl ABI 重建 XS 模块并验证实际合并路径。不能用只返回成功的 Perl stub 伪造检测。

已有 `E565-draft-C98A` 记录了 OHOS 沙箱内 XML::Parser 加载受限及针对 `intltool-merge -x` 的 shim；`DRAFT-ohos-intltool-toolchain-stub` 建议用 stub 让配置通过。本条新增的可独立复用边界是：以 `USE_NLS` 对生成检查做条件化、在 NLS 关闭时仍保留 `po/check` 所需真实工具，并以实际 Perl ABI 缺符号错误区分“模块路径缺失”与“模块二进制不可加载”。
