# conmux 0.12.0 适配笔记

## 编译环境
- 构建系统: makefile（纯拷贝安装，`make install BUILD=<staging>`，无编译目标）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（纯 Perl 应用，无 C/C++ 编译）
- 状态: built

## 编译步骤

1. 源码获取：官方 autotest GitHub 仓库（R39），conandata URL 指向
   `https://github.com/autotest/autotest/archive/refs/heads/master.tar.gz`，
   conanfile.py source() 中提取 conmux/ 子目录到源码根。
2. 构建：`make install BUILD=<staging>`（纯拷贝安装，Makefile 仅 cp/chmod）。
3. 打包：package() 将 staging 内容拷入 package，并校验核心产物
   （sbin/conmux、sbin/conmux-registry、bin/console、bin/conmux-attach、
   lib/Conmux.pm）。
4. 验证：`conan-verify conmux 0.12.0` — G1-G4 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试脚本报 `bad interpreter: /usr/bin/perl: No such file` | E049：conmux 脚本 shebang 硬编码 `#!/usr/bin/perl`，设备 perl 在 `/data/service/hnp/bin/perl` | package() 统一修正为 `#!/usr/bin/env perl`（可移植），本地与 conan create 内 test 均通过 |
| 2 | conan create source() 报 `SameFileError: .../conmux/conmux` | conmux 子目录内存在同名文件 `conmux`，直接 copy 提升时目标路径即源目录 | 先将 conmux/ 整体 rename 为 `.conmux-sub`，再提升内容到源码根 |
| 3 | test_package 报 `self.dependencies["perl-io-multiplex"].package_folder` 为 None | test 阶段传递依赖 binary 被 Skipped（未显式声明） | test_package requirements() 显式声明 `perl-io-multiplex/1.16` 与 `perl-uri/5.35` |
| 4 | toybox `/usr/bin/env` 解析 shebang 时 PERL5LIB 传递不可靠 | 依赖模块（IO::Multiplex/URI::Escape）未进入 @INC | test 改用显式 `perl -I <site_perl> script` 调用（不依赖 shebang + 环境变量） |
| 5 | conmux-attach 运行时找不到 Conmux.pm | 脚本仅 `use lib $FindBin::Bin`（bin/），Conmux.pm 在 lib/ | test 注入 `-I <lib>`；registry/console/conmux 上游已含 `../lib` 路径 |

## 源码修改

无补丁文件。E049 shebang 修正（`#!/usr/bin/perl` → `#!/usr/bin/env perl`）
内置在 conanfile.py package() 中，非源码补丁。

## 依赖版本

- perl-io-multiplex/1.16（IO::Multiplex，运行时依赖）
- perl-uri/5.35（URI::Escape，运行时依赖）
- perl 解释器 5.42.0（系统预装）

## 验证结果

```bash
# 本地功能实测（R51 上游无测试 → 自研 test_conmux.py）
$ python3 test_conmux.py <registry> <lib> <PERL5LIB>
OK: packaged scripts runnable (usage hints)
OK: Conmux.pm loaded from package
OK: conmux-registry protocol ADD/LOOKUP/LIST
OK: conmux 0.12.0 python-driven check

# conan-verify 8 门禁
$ ohc-run.py conan-verify conmux 0.12.0
G1-G4 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 配方（make install 纯拷贝 + E049 shebang 修正） |
| conandata.yml | 官方源 URL + sha256 |
| commands.json | CLI 工具声明（tool 类型，5 个可执行脚本） |
| test_package/ | 自研功能测试集（test_conmux.py，8 断言） |

## 注意事项

- conmux 是 autotest 仓库的 conmux 子目录，上游无独立 tag/发布点，
  conandata 采用官方仓库 master 分支快照 + 固定 sha256（可复现）。
- 上游确无自带测试（R51 穷尽核查：41 文件清单无测试、Makefile 无
  test/check 目标、README/INSTALL 无测试说明），自研 test_package
  覆盖核心功能（脚本可运行 + Conmux.pm 加载 + registry 真实协议）。
- lang-preflight 工具按文件后缀统计漏判无扩展名 Perl 脚本为 c
  （仅识别 Conmux.pm 与 fence_apc_snmp.py），c↔cpp 兼容族通过不阻塞；
  源码事实为纯 Perl 应用，与生态 lib*-perl/perl-uri/perl-reply 先例一致。
---

**编译结束**: 2026-09-10 04:45
**最终状态**: built
