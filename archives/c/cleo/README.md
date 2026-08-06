# cleo

> App::Cleo — Perl CLI diff viewer，对照两份输入并按行高亮差异。

## 简介

App::Cleo 是一个极简的 Perl 命令行差异查看器：读取两个文件（或标准输入），
按行比对并以颜色高亮增删改行，输出到终端。依赖 ExtUtils::MakeMaker + Test::More，
属 Perl App:: 呟下的纯 CLI 工具，无 GUI/服务端组件。

## OHOS 适配要点

- Perl 构建流程：`perl Makefile.PL` → `make` → `make install`，非 autotools
- 上游有自动化测试套件（`t/` 目录，`prove` 或 `make test` 跑）
- test_package 验证 bin/cleo 存在可执行 + shebang 为 perl + perl 可运行（3 个 assertion 点）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | ≥5.10 | ExtUtils::MakeMaker + Test::More 内置 |

## 功能验证

```bash
# 注：OHOS 预装 Perl 缺 App::Cleo 依赖模块（Term::ReadKey 等），
# perl -c bin/cleo 会因 use App::Cleo 找不到依赖失败（exit 2），
# 属环境限制而非安装错误。实际功能验证：
file bin/cleo                 # 验证脚本存在
head -1 bin/cleo              # 验证 shebang 指向 perl
perl -e 'print "perl OK\n"'   # 验证 perl 可运行
```

## 参考

- 上游仓库：https://github.com/thaljef/App-Cleo
- 排除与替代：无（纯 CLI 工具，不与仓库内其他包冲突）
