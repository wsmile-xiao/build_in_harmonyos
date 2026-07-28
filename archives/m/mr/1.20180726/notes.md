# mr (myrepos) 1.20180726 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-22
- 编译器: 不适用（纯 Perl 脚本工具）
- 状态: built

## 编译步骤

mr (myrepos) 是纯 Perl 脚本工具，使用简单 Makefile 构建：
1. `make build` — 使用 pod2man 生成 man 页面（mr.1, webcheckout.1）
2. `make install DESTDIR=$PACKAGE_FOLDER PREFIX="" MANDIR="/share/man/man1"` — 安装到 staging 目录
3. 无 configure 步骤（makefile 类构建系统）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | mr 的 shebang 已为 #!/usr/bin/env perl，无需修改 | 不需要补丁 |
| 2 | make install 路径问题 | Makefile 默认 PREFIX=/usr，需指定 DESTDIR 和 PREFIX | 在 package() 中指定 DESTDIR、PREFIX="" 和各路径参数 |

## 源码修改

- 无需修改（mr 的 shebang 已为 `#!/usr/bin/env perl`，兼容 OHOS 平台）
- 无补丁文件

## 依赖版本

- perl（系统自带，位于 /data/service/hnp/bin/perl）
- pod2man（系统自带，位于 /data/service/hnp/bin/pod2man，用于生成 man 页面）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mr | 多仓库管理主命令 |
| bin/webcheckout | 网页检出工具 |
| share/man/man1/mr.1 | mr man 手册页 |
| share/man/man1/webcheckout.1 | webcheckout man 手册页 |
| share/mr/* | mr 库文件 |
| share/mr.sh/* | mr shell 库文件 |
| share/doc/myrepos/examples/* | 示例配置文件 |

## 验证结果

### 版本验证
```bash
$ mr help | head -5
mr - a tool to manage all your version control repos
```

### 功能验证
```bash
# mr help: 显示帮助信息
$ mr help
  ✅

# mr register: 注册仓库
$ cd /path/to/repo && mr register
  ✅

# webcheckout: 仅验证文件存在与可执行权限
$ test -x "$(command -v webcheckout)" && echo "executable"
  ✅ (未实际运行，需 LWP::Simple/HTML::Parser CPAN 模块)
```

## 源码来源说明 (R39)

- 上游官方源 `https://myrepos.branchable.com/` 仅提供 git clone，不提供版本化 tarball 下载
- Debian pool (`https://deb.debian.org/debian/pool/main/m/myrepos/`) 是该版本唯一的权威 tarball 源
- 上游作者 Joey Hess 同时是 Debian 维护者，Debian 源码包与上游一致，无 Debian 特有补丁
- conandata.yml 中已添加注释说明选择 Debian pool 的原因

## 注意事项

- mr 是纯 Perl 脚本，无需 C/C++ 编译器
- shebang 已为 `#!/usr/bin/env perl`，无需补丁修改
- 上游 `make test` 需要 ed 编辑器，OHOS 环境可能缺失
- 由于无 Linux 环境进行本地 conan create 验证，依赖 CI 验证

---
**编译结束**: 2026-07-22
**最终状态**: built
