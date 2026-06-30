# perl-net-sftp-foreign 1.93-r0 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Perl 模块构建系统, custom)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (纯 Perl 模块，实际不涉及 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built (conan-verify 全部通过)

## 编译步骤

Net::SFTP::Foreign 是一个纯 Perl 模块（无 XS/C 代码），使用 ExtUtils::MakeMaker 构建系统。
编译过程非常简单，无需任何平台适配：

```bash
# 1. 下载并解压源码
tar xzf Net-SFTP-Foreign-1.93.tar.gz
cd Net-SFTP-Foreign-1.93

# 2. 生成 Makefile
perl Makefile.PL

# 3. 编译（实际为 Pod 文档处理和 .pm 文件准备）
make

# 4. 安装到 staging 目录
make install DESTDIR=$STAGING_DIR PREFIX=/
```

Conan 配方通过 `conan-init` 自动生成，`package()` 方法从 staging 目录的 `site_perl/`
子目录提取 `.pm` 文件到 `lib/`，通过 `PERL5LIB` 环境变量实现模块发现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | notes.md 为模板 | conan-init 自动生成后未填充 | 根据实际编译过程填写完整 |
| 2 | manifest.yaml sha256 为空 | conan-init 生成时未回填 | 从 conandata.yml 同步 sha256 值 |
| 3 | manifest.yaml build.system 标记为 autotools | 自动检测误判 | 修正为 custom (ExtUtils::MakeMaker) |
| 4 | 缺少测试报告 | finish 流程未生成 test-report | 参照 perl-dbd-pg 经验创建功能测试报告 |

**与 perl-dbd-pg 编译经验对比**：

| 对比项 | perl-dbd-pg (XS 模块) | perl-net-sftp-foreign (纯 Perl) |
|--------|----------------------|--------------------------------|
| 构建系统 | ExtUtils::MakeMaker + C 编译 | ExtUtils::MakeMaker (纯 Perl) |
| 补丁 | 需要 2 个补丁 (Makefile, Makefile.PL) | 无需补丁 |
| XS/C 代码 | 有 (.so 文件) | 无 |
| SELinux 限制 | 受 HMDFS 限制，XS 模块需安装到系统目录 | 不受限，纯 Perl 可从用户目录加载 |
| 外部依赖 | PostgreSQL libpq | 无 (全部为 Perl 核心模块) |
| conan-verify | 部分 FAIL (quality-report) | 全部 PASS |

## 源码修改

无。纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 系统自带 (aarch64-linux) |
| Scalar::Util | 核心 | Perl 5.42.0 内置 |
| Time::HiRes | 核心 | Perl 5.42.0 内置 |
| Test::More | 核心 | Perl 5.42.0 内置 |
| File::Spec | 核心 | Perl 5.42.0 内置 |
| Cwd | 核心 | Perl 5.42.0 内置 |
| IO::Select | 核心 | Perl 5.42.0 内置 |
| POSIX | 核心 | Perl 5.42.0 内置 |

所有依赖均为 Perl 核心模块，无需额外安装。

## 验证结果

### Conan 验证 (conan-verify)

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-net-sftp-foreign 1.93-r0
# G0: ✅ PASS (构建系统: unknown, 跳过预查询)
# G1: ✅ PASS (配方完整性检查)
# G2: ✅ PASS (conan create 成功)
# G3: ✅ PASS (无 bin/ 目录, 纯库包跳过 R26)
# G4: ✅ PASS (lib/: 11 .pm, 5 其他)
# L2: ✅ PASS (无 bin/ 目录, 跳过 smoke test)
# L4: ✅ PASS (无可扫描 ELF 文件)
# L5: ✅ PASS (产物与基线一致, 13 个文件)
```

### 功能测试

```bash
$ perl -MNet::SFTP::Foreign -e 'print $Net::SFTP::Foreign::VERSION'
1.93

# 全部 11 个子模块加载成功
# 50+ API 方法可用 (new, get, put, ls, stat, mkdir, rmdir 等)
# 对象创建和错误处理正常
# Constants 导出正常 (SSH2_FX_OK=0, SSH2_FX_EOF=1)
# Attributes set/get 正常 (size, perm)
# Buffer 操作正常 (put_int32, put_str, bytes)
# 无 SELinux 限制 (纯 Perl 可从用户目录加载)
# ssh 和 sftp 命令可用
```

详细测试报告见 `reports/test-report.md`。

## 注意事项

1. **纯 Perl 模块优势**: 与 perl-dbd-pg 等 XS 模块不同，Net::SFTP::Foreign 不涉及 C 编译，
   不产生 .so 文件，因此不受鸿蒙 SELinux HMDFS 限制影响，可直接从用户目录加载使用。

2. **运行时依赖**: 模块通过外部 `ssh` 命令实现 SFTP 连接。系统已安装 `/usr/bin/ssh` 和
   `/usr/bin/sftp`，运行时连接功能可用。

3. **PERL5LIB 配置**: Conan 配方通过 `runenv_info.prepend_path("PERL5LIB", ...)` 设置
   模块搜索路径。使用时需 `source conanrun.sh` 或通过 `conan install` 自动配置。

---

**编译结束**: 2026-06-26 18:12
**最终状态**: built (conan-verify 全部通过, 文档已完善)
**功能测试**: 2026-06-30, 全部通过
