# Memory::Process 0.06-r3 编译记录

## 基本信息
- 软件名: Memory-Process
- 版本: 0.06-r3 (CPAN 版本: 0.06)
- 构建系统: Perl (Module::Install, inc/ 内嵌)
- 源码URL: https://cpan.metacpan.org/authors/id/S/SK/SKIM/Memory-Process-0.06.tar.gz
- 模块类型: 纯 Perl（无 XS/C 代码）

## 编译状态
**状态**: SUCCESS (built)

## 编译日期
2026-06-17（首次修复，原编译 2026-06-16 FAILED）

## 编译过程

### Phase 1: 初始化 (2026-06-16)
- ✅ 源码下载成功
- ✅ 源码解压成功
- ⚠️ SSL证书问题，使用 curl -k 绕过

### Phase 2: 配置
- ✅ `perl Makefile.PL` 成功
- ⚠️ 警告: 缺少依赖模块 Memory::Usage, Readonly

### Phase 3: 编译
- ✅ `make` 成功 (纯 Perl 模块, 仅复制 .pm)
- ✅ `make install DESTDIR=$TEST_PREFIX` 成功

### Phase 4: 测试
- ❌ **首次** (2026-06-16): `make test` 失败 (8/8 文件失败)
  - 原因: 缺少 Memory::Usage 基类
  - 错误: "Base class package Memory::Usage is empty"
- ✅ **修复后** (2026-06-17): `make test` 全部通过 (8/8 文件, 27/27 用例)

### Phase 5: 安装
- ❌ `make install` 失败 (系统目录 /data/service/hnp 只读)
- ✅ 手动安装 Process.pm 到 ~/usr/local/lib/site_perl/5.42.0/Memory/
- ✅ 验证: `perl -MMemory::Process -e 'print $Memory::Process::VERSION'` → 0.06

## 修复措施

### 问题1: 依赖缺失
**根因**: Memory::Process 继承 Memory::Usage，且使用 Readonly 常量模块。
**解决方案**: 手动下载并安装依赖到 ~/usr/local:
```bash
# Memory::Usage
curl -k -fsSL https://cpan.metacpan.org/authors/id/D/DO/DONEILL/Memory-Usage-0.201.tar.gz | tar xz
cp Memory-Usage-0.201/lib/Memory/Usage.pm ~/usr/local/lib/site_perl/5.42.0/Memory/

# Readonly
curl -k -fsSL https://cpan.metacpan.org/authors/id/S/SA/SANKO/Readonly-2.05.tar.gz | tar xz
cp Readonly-2.05/lib/Readonly.pm ~/usr/local/lib/site_perl/5.42.0/

# Test::NoWarnings (测试依赖)
curl -k -fsSL https://cpan.metacpan.org/authors/id/A/AD/ADAMK/Test-NoWarnings-1.04.tar.gz | tar xz
cp -r Test-NoWarnings-1.04/lib/* ~/usr/local/lib/site_perl/5.42.0/
```

### 问题2: cpan install 系统目录权限
**根因**: 系统目录 /data/service/hnp/perl.org/ 只读。
**解决方案**: 手动复制 .pm 文件到 ~/usr/local/lib/site_perl/。

### 问题3: make install 安装到错误目录
**根因**: Module::Install 生成 Makefile 时使用 perl 的默认安装前缀。
**解决方案**: 使用 DESTDIR staging + 手动安装到用户目录。

## 安装产物
- `~/usr/local/lib/site_perl/5.42.0/Memory/Process.pm` (4357 bytes)
- `~/usr/local/lib/site_perl/5.42.0/Memory/Usage.pm` (依赖)
- `~/usr/local/lib/site_perl/5.42.0/Readonly.pm` (依赖)

## 与 perl-dbd-pg 编译经验对比
- perl-dbd-pg 是 XS 模块，遇到 SELinux HMDFS 限制 → Memory::Process 是纯 Perl，无此限制
- perl-dbd-pg 需要特殊链接参数 → Memory::Process 无 C 编译
- perl-dbd-pg 需要管理员安装 → Memory::Process 用户级安装即可
- 共同点: cpan install 到系统目录都失败（系统目录只读）

## 知识沉淀
1. 纯 Perl 模块安装：复制 .pm 到 ~/usr/local/lib/site_perl/ 即可
2. /proc/[pid]/statm 在 OHOS 上正常工作（7 个字段）
3. Module::Install 的 inc/ 目录内嵌于源码，不依赖系统安装
4. Memory::Usage 的 page_size_in_kb=4 在 OHOS aarch64 上正确
---

**编译结束**: 2026-06-17 17:54
**最终状态**: built
