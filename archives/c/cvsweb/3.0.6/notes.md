# cvsweb 3.0.6 适配笔记（HarmonyOS PC · 纯 Perl CGI 应用打包）

## 定位
- cvsweb 是 FreeBSD 的 CVS 仓库 Web 界面（WWW CGI script to browse CVS repository trees）。
- **纯 Perl CGI 应用**（cvsweb.cgi + cvsweb.conf + icons/css），无 C 编译产物 → 走脚本打包路径。

## 关键适配
- **依赖捆绑**：cvsweb.cgi 依赖 `IPC::Run` 与 `URI::Escape`，而 OHOS perl 5.42.2 为精简构建（无这些扩展模块）。在 source() 中捆绑下载纯 Perl 模块（IPC-Run-20220807.0、URI-5.28，均无 XS），解压合并到 `perl-lib/` 随包安装；运行/自检时 `PERL5LIB` 指向该目录。
- **语法自检**：build() 与 test_package 用 `perl -T -c cvsweb.cgi`（`-T` 匹配 shebang 的 taint 模式；不带 `-T` 会报 `"-T" is on the #! line`）。
- 上游无正式测试套件（CGI 应用无 make check/CTest），如实声明 `upstream_tests: []`，以 `perl -T -c` 语法自检作为可验证验证方式。

## 状态
built（conan-verify 通过；纯脚本应用无 ELF 产物）

## 编译步骤

```bash
conan create archives/c/cvsweb/3.0.6 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build()：纯 Perl 脚本无编译，仅做语法自检
cd $source_folder && perl -T -c cvsweb.cgi
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't locate IPC/Run.pm in @INC`（cvsweb.cgi line 100） | OHOS perl 5.42.2 精简构建无 IPC::Run/URI::Escape 扩展模块 | source() 捆绑纯 Perl 模块（IPC-Run/URI，均无 XS）到 perl-lib/，PERL5LIB 指向 |
| 2 | `"-T" is on the #! line, it must also be used on the command line` | cvsweb.cgi shebang `#!/usr/bin/perl -T`（taint 模式），`perl -c` 不带 -T 不匹配 | 自检命令用 `perl -T -c` |
| 3 | 上游无测试套件 | CGI 应用无构建系统/测试目标 | 如实声明 `upstream_tests: []`，以 `perl -T -c` 语法自检为可验证验证（R9 不伪造） |

## 上游测试结果

```bash
$ perl -T -c cvsweb.cgi（PERL5LIB=.../perl-lib）
cvsweb.cgi syntax OK
```

- 上游无正式测试套件（0/0，如实声明）；自检 `perl -T -c` 通过（syntax OK）。

## 交付物

| 文件 | 说明 |
|------|------|
| libexec/cvsweb/cvsweb.cgi | 主 CGI 脚本（perl -T shebang） |
| libexec/cvsweb/cvsweb.conf{,-freebsd,-netbsd,-openbsd,-ruby} | 配置文件 |
| libexec/cvsweb/icons/ css/ enscript/ | 静态资源 |
| libexec/cvsweb/perl-lib/ | 捆绑的纯 Perl 模块（IPC::Run、URI::Escape） |

## 注意事项

- R38：cvsweb.cgi 是 CGI 脚本（非直接 CLI 工具），`cpp_info.bindirs=["libexec/cvsweb"]`；软件级需 commands.json 声明。
- R26：纯脚本无 .so 产物，系统同名库隔离不适用（G3 如实标注）。
- 运行时需 CVS 服务器/仓库（cvsweb 语义），本包交付脚本与配置。
- 纯 Perl 模块捆绑已获 SHA256 校验（IPC-Run 277d781d...、URI e7985da3...）。
---

**编译结束**: 2026-08-08 17:29
**最终状态**: built
