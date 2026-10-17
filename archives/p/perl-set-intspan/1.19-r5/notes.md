# perl-set-intspan 1.19-r5 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29（功能验证: 2026-07-01）
- 编译器: clang/clang++（纯 Perl 模块，实际未使用 C 编译器）
- 状态: published

## 编译步骤

1. 从 CPAN 下载 Set-IntSpan-1.19.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-set-intspan 1.19-r5`
3. 运行 `perl Makefile.PL` 配置（生成 Makefile）
4. 运行 `make` 编译（仅复制 .pm 文件到 blib 目录）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
6. 运行 `make test` 执行单元测试（1947 个测试全部通过）
7. 生成 Conan 配方：`ohc-run.py conan-init perl-set-intspan 1.19-r5`
8. 验证 Conan 配方：`ohc-run.py conan-verify perl-set-intspan 1.19-r5`
9. 收尾归档：`ohc-run.py finish perl-set-intspan 1.19-r5 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，无 C 编译需求 | 无需任何补丁或修改 |

**与 perl-dbd-pg 编译经验对比**：
- perl-dbd-pg 是 XS 模块（含 C 代码），需要 `-nostartfiles -nodefaultlibs -lc` 绕过鸿蒙 CRT 文件缺失
- perl-set-intspan 是纯 Perl 模块，无需 C 编译，不受 CRT 问题影响
- perl-dbd-pg 受 SELinux HMDFS 限制，XS 动态库需安装到系统目录
- perl-set-intspan 无动态库，不受 SELinux 限制
- 两者均使用 ExtUtils::MakeMaker 构建系统，在鸿蒙上原生兼容

## 源码修改

无补丁、无源码修改。原始源码可直接编译。

## 依赖版本

### 运行依赖
- perl 5.42.0（系统预装于 `/data/service/hnp/bin/perl`）

### 编译依赖
- 无（纯 Perl 模块，仅需 perl 本身）

## 验证结果

### 单元测试
```bash
$ make test
# 20 个测试文件，1947 个测试，全部通过
All tests successful. Files=20, Tests=1947, 1 wallclock secs
```

### 功能测试（鸿蒙平台）
```bash
$ conan install --requires=perl-set-intspan/1.19-r5@ohpcd/stable --build=perl-set-intspan/1.19-r5@ohpcd/stable
$ export PERL5LIB="$PACKAGE_DIR/lib/perl5"
$ perl functional_test.pl
# 61 项功能测试全部通过，覆盖 18 个 API 类别
Total tests: 61, Passed: 61, Failed: 0
Result: ALL TESTS PASSED ✅
```

### Conan 验证
```bash
$ conan test test_package perl-set-intspan/1.19-r5@ohpcd/stable
# G0-G4 + L2/L4/L5 全部门禁通过
# test_package: Set::IntSpan test OK
```

## API 行为说明

- `insert($n)` / `remove($n)` 只接受单个整数参数
- 范围插入应使用 `union(Set::IntSpan->new("range"))`
- 传入字符串给 `insert()` 会触发 Perl 数值强制转换（"10-15" 变为 10）
- 所有集合运算（union, intersect, diff, complement）均正确处理 Set::IntSpan 对象

## 注意事项

1. 纯 Perl 模块，跨平台兼容性极佳，无需任何平台适配
2. Conan 配方中 `package()` 方法将 .pm 文件从深层 Perl 安装路径展平到 `lib/perl5/Set/` 目录
3. 消费者通过 `PERL5LIB` 环境变量找到模块（Conan 自动设置）
4. `settings.os` 检查使用 `in ("Linux", "OHOS")` 符合 R32 规范

---

**编译结束**: 2026-06-29 20:19
**功能验证**: 2026-07-01
**最终状态**: published
