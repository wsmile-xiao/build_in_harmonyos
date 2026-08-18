# perl-number-misc 1.2 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 通过MetaCPAN API查找正确的下载URL（CPAN模块名为Number-Misc，作者MIKO）
2. 使用curl -L手动下载源码包到$TMPDIR/builds/（如遇SSL证书问题，先安装ca-certificates或仅在开发环境临时使用--insecure，正式CI构建通过conandata.yml的sha256校验保障完整性）
3. ohc-run.py init-build（检测到已有tarball，跳过下载，执行解压和归档初始化）
4. cd $BUILD_SRC_DIR
5. perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
6. make -j2（构建成功）
7. make test（31个测试全部通过）
8. make install DESTDIR=$TEST_PREFIX（安装到staging目录）
9. conan-init生成Conan配方（修正为Perl专用配方）
10. conan-verify验证（所有门禁通过）
11. finish完成归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py下载SSL证书验证失败 | HarmonyOS环境缺少CA证书 | 手动下载源码包到$TMPDIR/builds/目录（建议安装ca-certificates解决根因，下载后须通过sha256校验确认文件完整性） |
| 2 | init-build初始搜索的URL返回404 | search_url找到的savannah URL不正确 | 通过MetaCPAN API查找正确的CPAN URL |
| 3 | conan-init生成的conanfile.py使用Autotools模板 | 自动检测误判构建系统 | 手动改写为Perl专用配方，参考perl-net-server的conanfile.py |
| 4 | conan-init生成的test_package使用CMake+C | 模板默认为C/C++项目 | 改写为Perl模块验证脚本 |
| 5 | finish中G0干净构建验证失败 | clean_verify尝试运行./configure但Perl模块没有configure脚本 | 已知限制，conan-verify(G2)的conan create已验证配方正确 |

## 源码修改

无源码修改。纯Perl模块，原始源码无需适配即可在OHOS上编译。

## 依赖版本

无外部依赖。仅需要Perl 5.003+（核心模块）。

## 验证结果

### make test
```
t/test.t .. ok
All tests successful.
Files=1, Tests=31, 1 wallclock secs
Result: PASS
```

### conan-verify
```
G1: PASS (配方完整性)
G2: PASS (conan create 干净构建)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性)
L2: PASS (smoke test, 纯库包跳过)
L4: PASS (安全扫描, 无ELF文件)
L5: PASS (产物基线对比, 5个文件一致)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan配方（Perl ExtUtils::MakeMaker） |
| conandata.yml | 源码URL和SHA256 |
| test_package/conanfile.py | Perl模块加载验证 |
| reports/conan-verify-report.md | 门禁验证报告 |
| reports/baseline.json | 产物基线 |

## 注意事项

- 纯Perl模块，无C/XS代码，不需要编译器参与实际编译
- Conan配方的package_info()中libs为空，通过PERL5LIB环境变量提供模块路径
- test_package使用VirtualRunEnv生成器，验证perl -MNumber::Misc加载
- 纯Perl模块不受SELinux HMDFS限制（与perl-dbd-pg的XS模块不同），可直接从用户目录加载
- is_numeric()实现内部移除逗号后检查，POD文档示例标注为false但实际返回true（上游已知问题）

## 功能测试（2026-07-01 补充）

### 测试环境
- Perl: 5.42.0 (aarch64-linux)
- 模块路径: Conan包缓存 (~/.conan2/p/b/perl-98791a730195e/p/lib)

### 测试结果

| 测试套件 | 测试数 | 通过 | 失败 | 结果 |
|---------|--------|------|------|------|
| 原始测试套件 (t/test.t) | 31 | 31 | 0 | ✅ PASS |
| 自定义功能测试 | 42 | 42 | 0 | ✅ PASS |
| Conan消费者安装 | - | - | - | ✅ PASS |
| SELinux/HMDFS兼容性 | - | - | - | ✅ PASS |
| **合计** | **73** | **73** | **0** | **✅ PASS** |

### 测试覆盖范围
- is_numeric(): 12项（含convertible选项）
- to_number(): 4项（含always_number选项）
- commafie(): 4项（含自定义分隔符）
- zero_pad(): 3项
- rand_in_range(): 4项（含负数范围、参数交换、数组上下文）
- is_even()/is_odd(): 6项（含非数字输入）
- 遗留别名: 3项（isnumeric, tonumber, zeropad）
- 边界测试: 4项（零值处理）

### 与perl-dbd-pg对比
| 对比项 | perl-dbd-pg | perl-number-misc |
|--------|-------------|------------------|
| 模块类型 | XS (C代码编译为.so) | 纯Perl (.pm文本文件) |
| SELinux限制 | ❌ HMDFS路径无法加载XS | ✅ 无限制 |
| 依赖 | musl, libpq, pg_config, DBI | 无 |
| 补丁 | 2个 | 0个 |
| 管理员安装 | 需要(HNP包) | 不需要 |
| 用户直接可用 | 否(PurePerl模式受限) | 是(完全可用) |

### packaging产物
- `packaging/lib/Number/Misc.pm` (9407B)
- `packaging/lib/Number/Misc.pod` (4164B)
- `packaging/lib/aarch64-linux/perllocal.pod` (284B)
- `packaging/perl-number-misc-1.2-ohos-aarch64.tar.gz` (18967B)

---

**编译结束**: 2026-06-29 20:36
**功能测试完成**: 2026-07-01
**最终状态**: built (conan-verify通过，功能测试73项全部PASS，符合上库要求)
