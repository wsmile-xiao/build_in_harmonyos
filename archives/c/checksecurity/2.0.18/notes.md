# checksecurity 2.0.18 适配笔记

## 编译环境
- 构建系统: custom（纯 Perl/shell 脚本集，Makefile 仅做安装布局，无 C/C++ 编译）
- 编译日期: 2026-09-07
- 编译器: 不适用（无编译步骤；脚本解释器：perl 5.42 / /bin/sh）
- 状态: built

## 编译步骤

checksecurity 是 Debian 系统安全检查脚本集（bin/checksecurity 主脚本 +
plugins/check-* 插件 + etc 配置 + man 手册）。无 configure/编译，仅需安装布局：

```bash
make            # all 目标：仅输出提示，无构建
make install PREFIX=$TEST_PREFIX   # 复制脚本/配置/man 到安装前缀
```

验证安装产物：usr/sbin/checksecurity、usr/share/checksecurity/check-*（5 插件）、
etc/checksecurity/*.conf（5 配置）、usr/share/man/man8/*.8（5 man 页）全部就位。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib 下载 SSL 证书校验失败 | 本机 Python SSL 证书链缺失 | 用 curl 下载源码包到 `$HOME/tmp/builds/`，init-build 探测到已存在 tarball 即跳过下载 |
| 2 | init-build 默认把归档写入 SKILL 目录 | find_project_dir() 优先返回脚本所在项目 | 显式设置 `OHC_PROJECT_DIR=<工作区仓库>`，归档落位 `archives/c/checksecurity/2.0.18/` |
| 3 | 主脚本/插件 shebang 指向 /usr/bin/perl | OHOS 无 /usr/bin/perl（perl 5.42 由制品仓经 PATH 提供） | patch shebang → `#!/usr/bin/env perl`（checkbashisms 先例同款方案） |
| 4 | test_package 模板是 CMake/C 空壳 | conan-init 按 autotools 生成模板 | 改写为脚本包范式：独立 test_checksecurity.py，perl -c 实质语法校验 + 组件完整性断言（R34） |
| 5 | 主脚本运行需 root 权限 | 脚本内 `if ($> != 0)` 非 root 直接退出 | 如实声明：test_package 用 perl -c 语法校验 + 打包完整性核对（R35 口径，不伪装全功能运行） |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-bin-checksecurity.patch | 主脚本 shebang: `#!/usr/bin/perl ` → `#!/usr/bin/env perl` |
| 0002-plugins-check-iptables-logs.patch | perl 插件 shebang: `#!/usr/bin/perl -w` → `#!/usr/bin/env perl` |

## 依赖版本

- perl/5.42.2（制品仓已发布，ohpcd remote 验证存在；脚本经 PATH 解析）
- 运行时系统命令：df/awk/find/mount/mail 等（OHOS 基础组件，脚本直调）

## 验证结果

```bash
# 手动安装布局验证
make install PREFIX=$TEST_PREFIX && find $TEST_PREFIX -type f | wc -l  # 16 个文件
# 主脚本 perl 语法校验
perl -c usr/sbin/checksecurity   # syntax OK
# conan 完整验证（conan-verify / finish W3）
conan create ...                 # 见 .ci-result.json
```

上游测试核查：checksecurity 2.0.18 源码包 34 个文件，Makefile 无 check/test 目标，
debian/rules 无测试调用，上游无自动化测试套件（MANIFEST.yml 已如实申报）。
自研 test_package 13 项断言（perl 语法 ×2 + 主脚本存在 ×1 + 5 插件存在 + 5 配置存在）。
---

**编译结束**: 2026-09-08 00:45
**最终状态**: built
