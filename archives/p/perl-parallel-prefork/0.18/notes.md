# perl-parallel-prefork 0.18 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Parallel-Prefork-0.18.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-parallel-prefork 0.18`
3. 运行 `perl Makefile.PL PREFIX=/usr/local` 配置
4. 运行 `make` 编译（纯 Perl 模块，无 C 编译）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
6. 生成 Conan 配方：`ohc-run.py conan-init perl-parallel-prefork 0.18`
7. 验证 Conan 配方：`ohc-run.py conan-verify perl-parallel-prefork 0.18`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MYMETA.json/yml 版本号为 0.17 | 源码包中的元数据文件版本与实际版本不一致 | `perl Makefile.PL` 会自动重新生成正确的 MYMETA 文件，无需补丁 |
| 2 | `use Parallel::Prefork` 失败 | 运行时依赖 Proc::Wait3 是 XS 模块，其 .so 在 HMDFS 上无法加载（SELinux 限制） | 需将 Proc::Wait3.so 安装到 /data/service/hnp 系统目录 |
| 3 | conanfile.py 中 PERL5LIB 覆盖系统模块路径 | Conan 的 runenv_info 设置 PERL5LIB 后，用户安装的 Perl 模块路径被替换 | 消费者需手动追加 `~/usr/local/lib/perl5` 到 PERL5LIB |

## 源码修改

无需补丁。`perl Makefile.PL` 执行时会从源码自动提取正确版本号并重新生成 MYMETA.json/yml，覆盖源码包中的旧版本元数据。

## 依赖版本

### 运行时 Perl 模块依赖
| 模块 | 版本要求 | 类型 | OHOS 可用性 |
|------|---------|------|-------------|
| Class::Accessor::Lite | >= 0.04 | 纯 Perl | ✅ 可用 |
| List::MoreUtils | 任意 | 纯 Perl | ✅ 可用 |
| Proc::Wait3 | >= 0.03 | XS 模块 | ⚠️ .so 需安装到系统目录 |
| Scope::Guard | 任意 | 纯 Perl | ✅ 可用 |
| Signal::Mask | 任意 | 纯 Perl | ✅ 可用 |

### 编译依赖
- perl 5.42.0 (系统自带)
- ExtUtils::MakeMaker (perl 核心模块)

## 验证结果

```bash
# Conan 验证全部通过
$ ohc-run.py conan-verify perl-parallel-prefork 0.18
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS

# 模块文件完整性
Parallel/Prefork.pm: 11097 bytes ✅
Parallel/Prefork/SpareWorkers.pm: 4732 bytes ✅
Parallel/Prefork/SpareWorkers/Scoreboard.pm: 3996 bytes ✅

# 功能测试（使用 Proc::Wait3 纯 Perl stub）
模块加载: ✅ PASS
对象实例化: ✅ PASS
num_workers(): ✅ PASS
signal_all_children(): ✅ PASS
fork/waitpid 基本功能: ✅ PASS
prefork start/finish 周期: ✅ PASS
上游测试 05-before_after_fork.t: 2/2 PASS ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Parallel/Prefork.pm | 11097 bytes | 主模块文件 |
| Parallel/Prefork/SpareWorkers.pm | 4732 bytes | SpareWorkers 子模块 |
| Parallel/Prefork/SpareWorkers/Scoreboard.pm | 3996 bytes | Scoreboard 子模块 |

## 注意事项

1. **Proc::Wait3 .so 加载问题**: 运行时依赖 Proc::Wait3 是 XS 模块，其 .so 文件在 HMDFS 上无法加载（SELinux `hmdfs:s0` 上下文限制）。需要将 `Wait3.so` 安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Proc/Wait3/` 目录（`hnp_file:s0` 上下文）。这与 perl-dbd-pg 遇到的相同问题。

2. **PERL5LIB 路径覆盖**: Conan 的 `package_info()` 设置 PERL5LIB 后会覆盖系统默认的 site_perl 路径。消费者需要手动将 `~/usr/local/lib/perl5` 追加到 PERL5LIB 以确保其他 Perl 模块可用。

3. **纯 Perl 模块**: Parallel::Prefork 本身是纯 Perl 模块，不包含任何 .so 文件，编译无需特殊链接参数。所有编译复杂性来自其运行时依赖 Proc::Wait3。

---

**编译结束**: 2026-07-03 16:52
**功能测试**: 2026-07-06
**最终状态**: built (编译成功，功能验证通过，Proc::Wait3 .so 加载需管理员安装)
