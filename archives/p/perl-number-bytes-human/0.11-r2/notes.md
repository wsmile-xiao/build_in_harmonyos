# perl-number-bytes-human 0.11-r2 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker) — 纯Perl模块
- 编译日期: 2026-06-29
- 编译器: clang/clang++ (纯Perl模块无需C编译器)
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL` 从 CPAN 下载 Number-Bytes-Human-0.11.tar.gz (SSL证书问题，使用-kL绕过。安全风险: -k禁用TLS验证存在中间人攻击风险，conandata.yml中已配置sha256校验作为补偿措施，正式环境应配置正确CA证书而非使用-k)
2. 初始化: `python3 ohc-run.py init-build perl-number-bytes-human 0.11-r2 --url=... --no-download`
3. 生成Makefile: `PERL_CANARY_STABILITY_NOPROMPT=1 perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`
4. 编译: `make -j2` (仅复制 .pm 文件到 blib/)
5. 测试: `make test` (207个测试全部通过)
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. Conan配方: `ohc-run.py conan-init` + 手动修复conanfile.py为Perl构建系统
8. Conan验证: `ohc-run.py conan-verify` (所有门禁通过)
9. 归档: `ohc-run.py finish perl-number-bytes-human 0.11-r2 published` (降级为built)
10. 功能测试: 2026-07-01 完成 13 项功能测试全部通过，升级为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | 鸿蒙环境CA证书不完整 | 使用 `curl -kL` 下载（安全风险: -k禁用TLS验证存在中间人攻击风险，conandata.yml已配sha256校验作为补偿，正式环境应配置正确CA证书），然后 `--no-download` 模式初始化 |
| 2 | /tmp 只读 | 鸿蒙平台限制 (E002) | 使用 $TMPDIR 替代 /tmp |
| 3 | Conan env参数类型错误 | Conan 2.x要求env为列表而非字典 | 改用 os.environ 设置环境变量 |
| 4 | Conan build找不到Makefile.PL | basic_layout导致source和build目录分离 | 移除layout()方法，参照perl-net-server模式 |
| 5 | 自动生成的conanfile.py使用Autotools | conan-init默认生成autotools模板 | 手动重写为Perl Makefile.PL构建系统 |
| 6 | 知识图谱误匹配E053 | cc1plus不适用于纯Perl模块 | 无需处理，E053是C++相关，Perl模块不受影响 |

## 源码修改

无源码修改，无补丁。

## 依赖版本

- Perl 5.042000
- 无外部依赖（纯Perl核心模块）

## 验证结果

```
make test 结果:
  Files=12, Tests=207, 2 wallclock secs
  Result: PASS
  (2个POD测试跳过: 缺少Test::Pod和Test::Pod::Coverage)

conan-verify 结果:
  G0: PASS (预构建风险评估)
  G1: PASS (配方完整性)
  G2: PASS (conan create干净构建)
  G3: PASS (系统同名库隔离)
  G4: PASS (产物完整性)
  L2: PASS (smoke test, 纯库跳过)
  L4: PASS (安全扫描, 无ELF文件)
  L5: PASS (基线对比, 4个文件一致)

功能测试结果 (2026-07-01):
  1. 模块加载: PASS (版本 0.11)
  2. 基本格式化: PASS (7个数值正确)
  3. SI模式: PASS (KiB/MiB/GiB正确)
  4. 二进制模式: PASS (K/M正确)
  5. 反向解析: PASS (5个数值正确)
  6. 精度控制: PASS (0/2/3位精度正确)
  7. 舍入模式: PASS (round/ceil/floor正常)
  8. 大数值边界: PASS (P/E单位正确)
  9. 负数处理: PASS (负数格式化正确)
  10. 单元测试套件: PASS (207/207通过)
  11. Conan L1测试: PASS (模块加载+版本验证)
  12. 模块源码完整性: PASS (19410 bytes, SHA256一致)
  13. 平台兼容性: PASS (纯Perl, 无SELinux限制)
```

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| conanfile.py | archives/p/perl-number-bytes-human/0.11-r2/ | Conan配方 |
| conandata.yml | archives/p/perl-number-bytes-human/0.11-r2/ | 源码+补丁声明 |
| test_package/ | archives/p/perl-number-bytes-human/0.11-r2/ | L1测试包 |
| Human.pm | lib/Number/Bytes/Human.pm | Perl模块文件 |
| manifest.yaml (软件级) | archives/p/perl-number-bytes-human/ | 软件级元数据 |
| README.md (软件级) | archives/p/perl-number-bytes-human/ | 软件说明文档 |
| test-report.md | archives/p/perl-number-bytes-human/0.11-r2/reports/ | 功能测试报告 |
| quality-report.md | archives/p/perl-number-bytes-human/0.11-r2/reports/ | 质量报告 |
| reviewer-report.md | archives/p/perl-number-bytes-human/0.11-r2/reports/ | 上库评估报告 |

## 注意事项

- 纯Perl模块，不需要C/C++编译器
- conanfile.py使用Perl Makefile.PL构建系统，不使用Autotools/CMake
- PERL_CANARY_STABILITY_NOPROMPT=1 避免交互式提示
- G0干净构建验证中的configure失败是平台限制（无./configure脚本），不影响Conan验证
- 纯Perl模块不受SELinux HMDFS限制，与perl-dbd-pg(XS模块)不同，用户可直接使用
- 参照perl-dbd-pg 3.18.0编译经验，完善了test-report.md/quality-report.md/reviewer-report.md
- Conan默认profile使用os=OHOS，确保conan install命令正常工作

---

**编译结束**: 2026-06-29 20:05
**功能测试**: 2026-07-01 完成 13 项功能测试全部通过
**最终状态**: published
