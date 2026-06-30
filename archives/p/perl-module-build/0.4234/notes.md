# perl-module-build 0.4234 适配笔记

## 编译环境
- 构建系统: perl-module-build (Build.PL)
- 编译日期: 2026-06-12
- 编译器: clang 21.1.5 (aarch64-linux)
- Perl 版本: 5.42.0
- 状态: built (编译成功，待发布)

## 编译步骤

Module::Build 是纯 Perl 模块，使用 Perl 自身的构建系统（`perl Build.PL` → `./Build` → `./Build install`）：

```bash
# 1. 创建 Build 脚本
cd Module-Build-0.4234
perl Build.PL --install_base ~/usr/local

# 2. 构建
./Build

# 3. 运行测试
./Build test

# 4. 安装到 staging（DESTDIR 模式）
./Build install --destdir ~/tmp/test-install-perl-module-build-0.4234

# 5. 安装到本地（模拟用户部署）
./Build install --install_base ~/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试套件完整运行时超时 | 部分测试涉及 fork/Test::Harness，在 OpenHarmony 上较慢 | 采用逐个运行方式，全部通过 |

**说明**: Module::Build 作为纯 Perl 模块，编译过程中无平台兼容性问题，无需补丁。

## 源码修改

无补丁。源码无需任何修改即可在 OpenHarmony 平台编译安装。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0 | 系统预装 |

## 验证结果

```bash
$ perl -MModule::Build -e 'print $Module::Build::VERSION'
0.4234

$ config_data --help
Usage: /usr/local/bin/config_data [options]
  ...

$ perl Build.PL  # 端到端测试
Creating new 'Build' script ...
$ ./Build test
All tests successful. Files=1, Tests=3. Result: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-build-0.4234-ohos-aarch64.tar.gz | 400KB | 预编译包（36 个文件） |
| reports/test-report.md | — | 功能测试报告 |
| reports/quality-report.md | — | 质量门禁报告 |
| reports/reviewer-report.md | — | 上库评估报告 |

## 注意事项

1. **纯 Perl 模块无 SELinux 限制**: 与 perl-dbd-pg 的 XS 模块不同，Module::Build 在 HMDFS 上完全可用
2. **测试套件超时**: 完整 `./Build test` 在连续运行时可能超时，建议逐个运行或增加超时时间
3. **后续模块依赖**: 作为 Perl 构建基础设施，perl-dbd-pg 等模块依赖此软件提供 `Build.PL` 支持
---

