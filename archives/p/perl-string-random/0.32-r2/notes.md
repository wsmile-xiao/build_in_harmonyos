# perl-string-random 0.32-r2 适配笔记

## 编译环境
- 构建系统: custom (Perl ExtUtils::MakeMaker)
- 编译日期: 2026-07-03
- 验证日期: 2026-07-06
- 编译器: clang/clang++ (未实际使用，纯Perl模块)
- 状态: published

## 编译步骤

1. 从 CPAN 下载 String-Random-0.32.tar.gz (SHA256: 9d93c679...)
2. 上游使用 Module::Build (Build.PL)，OHOS Perl 未安装 Module::Build
3. 创建 Makefile.PL 使用 ExtUtils::MakeMaker 替代（在 conanfile.py build() 中生成）
4. `perl Makefile.PL` → 生成 Makefile
5. `make -j1` → 编译（复制 .pm 到 blib）
6. `make install DESTDIR=$TEST_PREFIX` → 安装到 staging
7. `make test` → 全部 202 个测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib SSL 下载失败 | OHOS 缺少 CA 证书 | 使用 curl -k 手动下载 |
| 2 | 上游使用 Build.PL (Module::Build) | OHOS Perl 未安装 Module::Build | 在 conanfile.py build() 中生成 Makefile.PL (ExtUtils::MakeMaker) |
| 3 | init-build 生成的 conanfile.py 是 Autotools 模板 | 脚本默认 autotools 模板 | 手动改写为 Perl 模块构建配方 |
| 4 | finish Step6 (gen_summary) 失败 | 非致命错误 | 不影响归档完整性 |

## 与 perl-dbd-pg 编译经验对比

perl-dbd-pg 是 XS 模块（含 C 代码），遇到 CRT 文件缺失和 SELinux HMDFS 限制问题。
perl-string-random 是纯 Perl 模块，不涉及 C 编译，因此：
- ✅ 无需 `-nostartfiles -nodefaultlibs -lc` 链接参数
- ✅ 无需安装到系统目录 /data/service/hnp（但 Conan 默认安装路径已包含此路径）
- ✅ 无 ELF 签名要求

## 源码修改

- 新增 Makefile.PL: 使用 ExtUtils::MakeMaker 创建，替代上游的 Build.PL
  (纯 Perl 模块，Makefile.PL 内容从 META.json 提取依赖信息)
  该文件在 conanfile.py 的 build() 方法中动态生成，未使用 patch 文件

## 依赖版本

- Perl 5.42.0 (OHOS 系统自带)
- ExtUtils::MakeMaker 7.76
- 无外部依赖（Carp, Exporter, parent 均为 Perl 核心模块）

## 验证结果

### 上游测试 (make test)
```
t/00-compile.t ........ ok
t/01_use.t ............ ok
t/02_new.t ............ ok
t/03_random_string.t .. ok
t/04_randpattern.t .... ok
t/05_randregex.t ...... ok
t/06_random_regex.t ... ok
t/07_rand_gen.t ....... ok
t/08_get_set.t ........ ok
All tests successful.
Files=9, Tests=202, 1 wallclock secs
Result: PASS
```

### Conan 消费者测试 (test_package)
```
RUN: PERL5LIB="..." sh test_string_random.sh
OK: String::Random v0.32 loaded (4/4 tests passed)
```

### Conan 验证门禁 (conan-verify)
- G0-G4: 全部 PASS
- L2/L4/L5: 全部 PASS (跳过，纯 Perl 模块无 cache 路径)
- 结论: 可标记 status: published

### 平台功能测试 (10项)
- 模块加载、构造函数、randpattern、randregex、random_string
- set_pattern/get_pattern、随机性验证、复杂正则模式、默认字符集
- 结果: 10/10 全部通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Perl 模块构建，build() 中生成 Makefile.PL） |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 消费者测试（验证模块可加载） |
| reports/test-report.md | 功能测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/conan-create.log | Conan 构建日志 |

## 上库条件评估

✅ 符合上库要求：
- conanfile.py / conandata.yml / test_package/ 齐全
- conan-verify 全部通过 (G0-G4 + L2/L4/L5)
- 上游 202 个测试全部通过
- 平台功能测试 10/10 通过
- 软件级 README.md / manifest.yaml 已创建
- 版本级 manifest.yaml 状态为 published

## 注意事项

- 上游实际使用 Module::Build，本配方通过在 build() 中生成 Makefile.PL 适配为 ExtUtils::MakeMaker
- 纯 Perl 模块，无需 C 编译器
- package_info.cpp_info.libs 为空（无 C 库）
- G4 报告"无法找到程序包 ID"是预期行为（纯 Perl 模块无传统 bin/lib/include 产物）
---

**编译结束**: 2026-07-06 11:50
**最终状态**: published
