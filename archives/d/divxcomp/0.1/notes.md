# divxcomp 0.1 适配笔记

## 软件定性

divxcomp 不是 C/C++ 库，而是一个 **纯 Perl/Tk GUI 脚本**（单文件
`divxcomp.pl`，104 行，DivX 码率计算器，2003 年唯一版本 0.1，上游已死）。
无构建系统、无编译步骤，适配形态为 application 型"脚本安装包"
（参照 album/4.18 纯 Perl 先例与 darkhttpd/1.17 application 先例）。

## 源码与 License

- 官方归档（Debian pool，事实上的官方分发渠道；上游主页 DNS NXDOMAIN）：
  https://deb.debian.org/debian/pool/main/d/divxcomp/divxcomp_0.1.orig.tar.gz
- SHA256: `ff6a8cf33579c6590ee2cd82755542c3e070d417b7a231609a25b76e1f65cd62`
  （本机 remote_source.py 下载校验 + 设备 curl 下载 sha256sum 校验一致；
  Scout 曾交叉校验 Ubuntu 镜像逐字节相同、snapshot.debian.org 元数据吻合）
- License: **GPL-2**。归档内 GPL.txt 为 GPLv2 全文；Debian copyright 归为
  GPL-2。注：脚本头注释字面为 "version 2 ... or any later version"
  （GPL-2-or-later），本仓按 Debian 口径统一标 GPL-2，此处记录差异。

## 适配步骤

1. conandata.yml 固定源码 URL + SHA256；conan `get()` 下载解包（无编译）。
2. 补丁 `patches/0001-ohos-headless-version-flag.patch`（+11 行，最小化）：
   在 `use Tk;` 之前的 BEGIN 块中处理 `--version`，打印 `divxcomp 0.1`
   并退出。BEGIN 块在编译期、加载 Tk 之前执行，因此 headless 环境
   （无 Perl::Tk、无 X11）也能查询版本。参照 darkhttpd
   0001-add-version-exit.patch 先例（为 L2 冒烟提供可执行入口）。
3. package()：脚本安装为 `bin/divxcomp`（Debian 同名），chmod 755；
   按 E037 将 shebang `#!/usr/bin/perl -w` 重写为
   `#!/data/service/hnp/bin/perl -w`（OHOS 无 /usr/bin/perl；重写在配方
   package() 内完成，同 album/4.18 先例，补丁不携带设备路径）；
   GPL.txt 进 licenses/，README/ChangeLog 进 share/divxcomp/。
4. test_package：VirtualRunEnv + conanrun 环境（包 bin/ 在 PATH），
   `test.sh` 执行 `divxcomp --version` 并断言输出 `divxcomp 0.1`。

## 测试事实（诚实记录）

- **上游测试套件：不存在（NO_UPSTREAM_TESTS）**。已核验（2026-09-13）：
  归档仅含 README / GPL.txt / divxcomp.pl / ChangeLog 四个文件；无
  make check / CTest / pytest / 测试脚本 / POD 自检；无构建系统，不存在
  可开启的测试开关。证据：本机 `runs-v2/divxcomp-0.1/scout/dl/` 解包目录
  与 `builder/sources/`（SHA256 校验）；设备
  `tmp/oh-device-porting-v2/divxcomp-0.1-verify/` 解包目录。
- **headless 功能验证不可行的原因**：脚本第 29 行无条件
  `MainWindow->new()`，`use Tk` 为编译期依赖；设备无 Perl::Tk
  （`perl -MTk` → Can't locate Tk.pm），CI 无 X11 display，`perl -c`
  都会在编译期失败（环境原因，非代码缺陷）。Perl::Tk 含 XS 并链接 X11，
  在 headless CI 引入不可行也不值得（Scout §4/§7 结论）。
- **实际验证**：test_package 通过补丁新增的 `--version` 入口真实调用
  打包产物（PATH 解析 bin/divxcomp，真实 Perl 解释器执行），
  断言输出 `divxcomp 0.1`。设备上预先人工验证：
  `tmp/oh-device-porting-v2/divxcomp-0.1-verify/` 中补丁应用 +
  shebang 重写 + 直接执行均输出 `divxcomp 0.1`（exit 0）。
- 不伪造上游测试、不虚构 PASS；GUI 计算功能的端到端验证需要用户侧
  Perl::Tk + X11 环境，已在 README/manifest 中如实标注。

## 白名单说明（ci/config/no_official_test.txt）

该白名单位于 `ci/**`（Builder 写入硬边界之外），本 run **未改动**。
CI L1 门控逻辑（build_and_test.sh）在无白名单条目时按
"test_package 是否真实执行" 判定（L1a/L1d/L1e），本包 test_package
真实执行且依赖打包产物（L1e 负向测试可证），L1 可如实通过。
若团队希望 L1 结果标记为 `skip: whitelisted (no official test)`，
需另行授权在 `ci/config/no_official_test.txt` 增加一行 `divxcomp`
（惯例：每个包适配提交各自追加，见 asmjit/fabric/astromatic/acpi_call
提交历史）。

## 限制与风险

- GUI 功能（码率计算界面）在 headless 环境不可运行，需用户侧提供
  Perl::Tk + X11；本适配保证脚本正确安装、解释器路径正确、版本可查询。
- 上游已死 20+ 年，无后续版本/补丁来源；源码溯源依赖 Debian pool
  （已多源锁定）。
- musl/aarch64 对纯 Perl 代码无影响。

## 知识沉淀

- knowledge/drafts/DRAFT-divxcomp-0.1-headless-perl-gui-packaging.md：
  纯 Perl/Tk GUI 脚本在 headless OHOS 的最小可用打包模式
  （配方内 shebang 重写 + BEGIN 块 --version + 上游无测试的诚实记录）。

---
**适配完成**: 2026-09-13
**最终状态**: built
