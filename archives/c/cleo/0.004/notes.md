# cleo 0.004 适配笔记

## 编译环境
- 构建系统: perl-makefile (ExtUtils::MakeMaker，Makefile.PL → make → make install)
- 编译日期: 2026-07-31
- 编译器: 无（Perl 脚本不编译 C/C++）
- 状态: built

## 上游
- URL: https://codeload.github.com/thaljef/App-Cleo/tar.gz/3e22cae6db3f54598990e8681eb0103376d067a4
- SHA-256: cfaa32b827fbb1d7825d32b3fd0c1c0cb7ad6d2a9fb0a56f57b61097b6a5c93b
- homepage: https://github.com/thaljef/App-Cleo
-性质: Perl CLI 库（App::Cleo），终端差异查看工具

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build cleo 0.004
   ```

2. 配置：Perl Makefile.PL（ExtUtils::MakeMaker）：
   ```bash
   PERL5LIB=$perl_Term_ReadKey/lib/perl5:$perl_Term_ANSIColor/lib/perl5:... \
   perl Makefile.PL INSTALL_BASE=$TEST_PREFIX
   ```

3. 编译：
   ```bash
   make
   ```

4. 安装到 staging：
   ```bash
   make install
   ```

5. 测试：
   ```bash
   make test
   # t/compile.t .. ok: 1/1 passed
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | Perl 模块依赖找不到 | cleo 依赖 Term::ReadKey/Term::ANSIColor/File::Slurp/Time::HiRes 5 个 Perl 模块 | 通过系统 perl 预装提供（CI 预装 perl + 模块），无 Conan 依赖声明 | — |
| 2 | 上游测试是 Perl Test::More 非 C 测试 | t/compile.t 是 `use_ok('App::Cleo')` Perl 模块加载测试 | 消费者测试 test_cleo.c 验证二进制存在 + shebang 为 perl（OHOS 环境未执行 perl -c，仅间接验证模块依赖链） | — |

## 源码修改

无补丁文件（cleo 源码无需修改，Perl 模块依赖通过 Conan 依赖注入）。

## 依赖版本

5 个 Perl 模块（Term::ReadKey/Term::ANSIColor/File::Slurp/Time::HiRes/ExtUtils::MakeMaker）
走系统 perl 预装提供（CI 预装 perl + 模块），无 Conan 依赖声明，
与 conanfile.py requirements()=pass 及 manifest.yaml dependencies=[] 一致。

## 验证结果

```bash
# cleo 脚本安装
file bin/cleo
# Perl script text executable

# Perl 模块加载验证（OHOS 环境未执行 perl -c，验证二进制存在 + shebang 为 perl）
test_cleo 验证 bin/cleo 存在、可执行、shebang 指向 perl

# 上游测试
make test
# t/compile.t .. ok: 1/1 passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cleo | Perl CLI 脚本（终端差异查看工具） |
| lib/App/Cleo.pm | Perl 模块 |

## 注意事项

1. **cleo 是 Perl CLI 库**，非 C/C++ 库——榜单 lang=cpp 标错了，实际是 Perl（App::Cleo）。
2. **Perl 模块依赖通过系统 perl 预装提供**（CI 预装 perl + 模块），无 Conan 依赖声明，消费者需系统预装 perl 模块。
3. **上游测试 t/compile.t 是 Perl Test::More use_ok('App::Cleo')**，消费者测试 test_cleo.c 验证二进制存在 + shebang 为 perl（OHOS 环境未执行 perl -c，仅间接验证 Perl 模块依赖链可加载）。

## 路径 B 申报

本库适配过程无通用问题可入知识图谱（Perl 模块依赖通过 Conan 包解决非通用问题，ExtUtils::MakeMaker 构建无平台特有障碍），**不走路径 B**，仅走路径 A（基础适配）。
