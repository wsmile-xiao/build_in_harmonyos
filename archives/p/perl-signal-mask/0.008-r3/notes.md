# perl-signal-mask 0.008-r3 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Signal-Mask-0.008.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-signal-mask 0.008-r3
3. 设置 PERL5LIB 环境变量（包含系统 Perl site_perl 路径，用于 IPC::Signal 依赖）
4. 运行 `perl Makefile.PL INSTALLDIRS=site` 配置
5. 运行 `make -j1` 编译
6. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
7. 生成 Conan 配方：ohc-run.py conan-init perl-signal-mask 0.008-r3
8. 验证 Conan 配方：ohc-run.py conan-verify perl-signal-mask 0.008-r3
9. 收尾归档：ohc-run.py finish perl-signal-mask 0.008-r3 built

> 注：PR 合并并 CI upload 成功后，状态从 `built` 更新为 `published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PERL5LIB 未设置导致 IPC::Signal 依赖找不到 | Signal::Mask 运行时依赖 IPC::Signal 模块，该模块安装在系统 Perl 路径 | 在 conanfile.py 的 build()/package() 中通过 `_get_perl5lib()` 方法自动构建 PERL5LIB 环境变量，包含系统 site_perl 路径 |
| 2 | 纯 Perl 模块无需 C 编译器工具链 | Signal::Mask 是纯 Perl 实现，不包含 XS/C 代码 | conanfile.py 的 `generate()` 方法为空（pass），不调用 CMake/toolchain |

## 源码修改

无补丁。Signal::Mask 0.008 是纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译。

## 依赖版本

### 运行时依赖
- IPC::Signal: 打包到 conan 包内 (lib/perl5/IPC/Signal.pm)，从 CPAN 下载源码并 bundle

### 编译依赖
- perl 5.42.0 (系统自带)
- make (系统自带)

## 验证结果

### Conan 验证
```
conan-verify: PASS (G0-G4 + L2/L4/L5 全部通过)
conan create: 成功，test_package 4 项测试全部通过
```

### 功能测试 (2026-07-01)
```
T1: Signal::Mask 模块加载 ✅
T2: Signal::Pending 模块加载 ✅
T3: 版本验证 (0.008) ✅
T4: IPC::Signal 依赖检查 ✅
T5: 信号掩码设置与清除 ✅
T6: Signal::Pending 接口 ✅
T7: 完整信号掩码+待处理信号周期 ✅
T8: 多信号掩码 (USR1/USR2/HUP) ✅
T9: 上游测试套件 (18/18 通过) ✅
```

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/site_perl/5.42.0/Signal/Mask.pm | 3148 bytes | Signal::Mask 模块 |
| lib/perl5/site_perl/5.42.0/Signal/Pending.pm | 2371 bytes | Signal::Pending 模块 |

## 注意事项

- Signal::Mask 是纯 Perl 模块，不涉及 C/XS 编译，无需 CRT 链接参数（与 perl-dbd-pg 等 XS 模块不同）
- 运行时依赖 IPC::Signal 模块，需确保系统 Perl 的 site_perl 路径在 PERL5LIB 中
- 信号掩码和待处理信号功能在 OpenHarmony 6.0 上行为与标准 Linux 一致

---

**编译结束**: 2026-06-29 20:20
**最终状态**: built (conan-verify 通过，待 PR 合并后 upload 更新为 published)
