# DRAFT-divxcomp-0.1-headless-perl-gui-packaging — 纯 Perl/Tk GUI 脚本在 headless OHOS 的最小可用打包：配方内 shebang 重写（E037）+ BEGIN 块 --version + 上游无测试的诚实记录

- 触发事件：divxcomp 0.1 适配（非 C/C++ 库，104 行 Perl/Tk GUI 脚本，2003 年唯一版本）
- 路径：Path A（工程适配）
- 编号：DRAFT-divxcomp-0.1-headless-perl-gui-packaging

## 现象

divxcomp 0.1 是纯 Perl/Tk GUI 脚本（DivX 码率计算器）：无构建系统、无
上游测试；`use Tk` 为编译期依赖且脚本无条件 `MainWindow->new()`。设备
只有 /data/service/hnp/bin/perl（无 /usr/bin/perl），无 Perl::Tk、无
X11 display——脚本在 headless 设备上连 `perl -c` 都无法通过（编译期缺
Tk，环境原因而非代码缺陷）。

## 根因与分析

1. 解释器路径：上游 shebang `#!/usr/bin/perl -w` 在 OHOS 上为
   bad interpreter（E037：OHOS 无 /usr/bin/perl、无 /usr/bin/env）；
2. GUI 依赖：Perl::Tk 含 XS 并链接 X11，headless CI 引入不可行也不值得，
   GUI 功能在设备上不可验证；
3. 测试缺位：上游归档仅 README/GPL.txt/divxcomp.pl/ChangeLog 四个文件，
   无任何测试入口与开关（NO_UPSTREAM_TESTS），CI L1 只能依赖
   test_package 真实执行来判定。

## 可复用处置模式（三步）

1. **shebang 在配方内重写，不进补丁**：package() 中
   `replace_in_file(..., "#!/usr/bin/perl -w", "#!/data/service/hnp/bin/perl -w", strict=False)`
   （同 album/4.18 先例），补丁只承载语义修改，不携带设备绝对路径；
   脚本安装为 `bin/<name>`（对齐发行版安装名）并 chmod 755；
2. **BEGIN 块 --version**：在 `use Tk;` 之前插入
   `BEGIN { if (grep { $_ eq '--version' } @ARGV) { print ...; exit 0 } }`。
   BEGIN 在编译期、加载 Tk 之前执行，headless 可查询版本——为 CI L2
   冒烟与 test_package 提供真实可执行入口（darkhttpd
   0001-add-version-exit.patch 同思路）。注意补丁必须保持原文件 LF，
   上下文锚点选文件头注释块结尾与 `use Tk;` 之间；
3. **测试诚实记录**：MANIFEST.yml `upstream_tests: []` 并写明四项证据
   （归档文件清单、无测试入口、无构建开关、GUI 编译期依赖导致
   headless 无法验证）；test_package 只做自建 `--version` 冒烟并声明
   "不冒充上游测试"；notes.md 记录 NO_UPSTREAM_TESTS 结论与证据路径。
   上游无测试的包**不一定要进 ci/config/no_official_test.txt**：CI L1
   无白名单条目时按"test_package 是否真实执行"判定（L1a/L1d/L1e），
   只要 test_package 真实调用打包产物即可如实通过；白名单位于 ci/**，
   受 Builder 写入硬边界约束，除非获授权否则不动。

## 实证

- 设备验证：tmp/oh-device-porting-v2/divxcomp-0.1-verify/ 中
  git apply 补丁成功；`perl divxcomp.pl --version` 输出 `divxcomp 0.1`；
  sed 重写 shebang + chmod 755 后直接执行同样通过；
- CI（ci/conan/build_and_test.sh，CI_PACKAGES=archives/d/divxcomp/0.1）：
  conan create + test_package 冒烟通过，L0/L1/L2 全部 PASS（结果见
  本 run builder 日志与 archives/d/divxcomp/0.1/manifest.yaml）。

## 跨项目适用

任何"纯解释型脚本 + 编译期 GUI/重依赖 + headless 目标环境"的打包
（perl/python/tcl GUI 小工具等）：解释器路径配方内重写（E037）、
BEGIN/`if __name__` 级别的轻量 --version 入口、上游无测试时以
test_package 真实产物调用 + 完整证据链代替，且不虚报测试来源。

## 边界与判断

- BEGIN 块方案只适用于"GUI 依赖在编译期加载"的脚本；若脚本启动即有
  副作用（写文件/联网），--version 入口应放在更早的参数分发处；
- 不要为了过 CI 而给 GUI 脚本引入 Xvfb/Tk 等重依赖；GUI 验证缺口应
  在 README/manifest 中对用户如实标注；
- 白名单（ci/config/no_official_test.txt）是"上游测试与 OHOS 环境不
  兼容"的正式声明通道，属于 ci/**，动它需明确授权。
