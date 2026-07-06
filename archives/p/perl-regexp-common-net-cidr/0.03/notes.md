# perl-regexp-common-net-cidr 0.03 适配笔记

## 编译环境
- 构建系统: makefile (ExtUtils::MakeMaker / 替换的 Makefile.PL)
- 编译日期: 2026-06-26 (初次) / 2026-06-29 (修复完善)
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -k -L -o Regexp-Common-net-CIDR-0.03.tar.gz https://cpan.metacpan.org/authors/id/B/BP/BPS/Regexp-Common-net-CIDR-0.03.tar.gz`
2. 初始化编译: `python3 ohc-run.py init-build perl-regexp-common-net-cidr 0.03 --url=...`
3. 生成 Makefile: `perl Makefile.PL INSTALLDIRS=site`（使用替换的 ExtUtils::MakeMaker 版本）
4. 编译: `make -j1`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make test`（无测试定义，跳过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 Makefile.PL 使用 Module::Install (inc::Module::Install) | Module::Install 在隔离环境中触发自动安装依赖，导致编译失败 | 替换为标准 ExtUtils::MakeMaker Makefile.PL |
| 2 | conanfile.py 硬编码 Perl 路径 (5.42.0) | 路径中硬编码了版本号和本地路径 | 改用 glob 动态发现 Perl 版本路径 + 从 Conan 依赖获取 |
| 3 | 未声明 Conan 依赖 | conanfile.py 没有 requirements()，通过硬编码 PERL5LIB 引用 Regexp::Common | 添加 requirements() 声明 perl-regexp-common/2024080801 |
| 4 | package_info() 硬编码路径 | 使用硬编码 lib/perl5 而非动态发现 | 改用 glob 动态发现 site_perl 路径 |
| 5 | test_package 硬编码本地路径 | 测试脚本中硬编码了 /storage/Users/currentUser/... 路径 | 改为动态检测系统 Perl site_perl 路径 + 从依赖包动态发现 |
| 6 | test_package 缺少功能测试 | 仅检查模块加载和版本 | 新增 IPv4 CIDR 模式匹配测试、无效输入拒绝测试、-keep 选项测试 |
| 7 | test_package 包含 conan 生成文件 | conan create 生成的临时文件被归档 | 清理 conanbuild.sh/conanrun.sh 等生成文件 |
| 8 | notes.md 为模板 | 未填充实际编译信息 | 填充完整的编译笔记 |
| 9 | 缺少软件级 README.md | 归档目录缺少 README.md | 创建软件级 README.md |

## 源码修改

无源码修改。在 conanfile.py 的 build() 方法中动态生成替换的 Makefile.PL（使用 ExtUtils::MakeMaker 替代 Module::Install）。

## Conan 配方变更 (2026-06-29)

### conanfile.py 修复
1. **添加 requirements()** — 声明 perl-regexp-common/2024080801 为 Conan 依赖
2. **移除硬编码 Perl 路径** — 改用 _get_perl5lib() 方法动态从 Conan 依赖 + 系统 Perl 路径构建 PERL5LIB
3. **统一打包路径** — 与 perl-regexp-common 保持一致，保留 site_perl 路径结构
4. **修复 package_info()** — 使用 glob 动态发现 site_perl 路径

### test_package/conanfile.py 修复
1. **移除硬编码本地路径** — 改为动态检测系统 Perl site_perl 路径
2. **增强功能测试** — 新增 IPv4 CIDR 模式匹配测试、无效输入拒绝测试、-keep 选项测试
3. **清理生成文件** — 移除 conan create 生成的临时文件和旧测试脚本
4. **使用 subprocess** — 采用与 perl-regexp-common test_package 一致的 subprocess 方式

## 依赖版本

- Regexp::Common (2024080801) — 通过 Conan 依赖 perl-regexp-common/2024080801 提供
- Perl 5.42.0 — 系统安装

## 验证结果

```bash
$ make test
No tests defined for this extension (跳过)

$ conan create archives/p/perl-regexp-common-net-cidr/0.03 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
perl-regexp-common-net-cidr/0.03: Package created
test_package: Regexp::Common::net::CIDR loaded successfully: OK
test_package: Version OK
test_package: CIDR pattern matching test OK
test_package: Keep option test OK
```

## 注意事项

- 本模块为纯 Perl 模块（无 XS/C 代码）
- 原始 Makefile.PL 使用 Module::Install，在隔离环境中会触发自动安装，已替换为标准 ExtUtils::MakeMaker
- 依赖 Regexp::Common，通过 Conan 依赖管理
- 无测试套件，功能测试通过 test_package 实现
- 支持 IPv4 CIDR 缩写格式（最少 2 个八位组，如 10.0/8），不支持单八位组（10/8）
- -keep 选项将地址存入 $1、前缀长度存入 $2
- conanfile.py 按照纯 Perl 模块模式编写，参考 perl-regexp-common 成功案例

---

**编译结束**: 2026-06-29
**最终状态**: published
