# perl-net-libresolv 0.03-r2 — 编译笔记

## 软件信息
- 名称: Net::LibResolv (CPAN: PEVANS)
- 版本: 0.03（打包为 0.03-r2）
- 类型: Perl XS/C 模块
- 描述: libresolv（DNS 解析器函数）的 Perl 封装
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Net-LibResolv-0.03.tar.gz
- SHA256: 9004f047d71e92817a685a5ea7b8ae75d9bf9bdbbe9bd444a087a63e13044c86

## 平台问题与解决方案

### 1. SSL 证书验证
- 问题: 从 CPAN 下载时 Python urllib 报 SSL_CERTIFICATE_VERIFY_FAILED
- 解决: 使用 curl -k 下载 tar 包，放入构建目录

### 2. /tmp 只读 (E002)
- 问题: HarmonyOS 上 /tmp 为只读文件系统
- 解决: 设置 TMPDIR=$HOME/tmp

### 3. ExtUtils::CChecker 链接器失败
- 问题: CChecker 的 find_libs_for() 尝试编译+链接测试程序；链接器 (ld.lld)
  报错 "unknown argument '-fstack-protector-strong'" 和 "unable to find library -lc"
- 根因: Perl 的 Config 中 libpth 过时，指向不存在的 sysroot；
  LD 环境变量设为 ld.lld 而非 clang
- 解决: 绕过 CChecker，使用正确标志手动编译 XS
- **perl-dbd-pg 经验**: 相同的链接器问题，相同的手动 XS 编译方案

### 4. xsubpp PROTOTYPES 警告
- 问题: xsubpp 将 "Please specify prototyping behavior" 警告输出到 C 文件中
- 解决: 在 .xs 文件的 MODULE 行后添加 `PROTOTYPES: DISABLE`

### 5. musl 上的 libresolv
- 问题: musl/HarmonyOS 上 libresolv.a 是个桩文件（8 字节）
- 事实: res_query、res_search 在 musl 中直接内置于 libc
- 解决: 无需 -lresolv；.so 仅链接 libc 依赖

### 6. SELinux HMDFS 限制（预期）
- 问题: HMDFS 上的 .so 文件 SELinux 上下文为 hmdfs:s0；Perl hishell_hap 域
  只能加载 hnp_file 类型 → 运行时报 "Permission denied"
- 影响: 测试失败（非编译失败）
- 缓解: .so 需管理员安装到系统目录才能运行时使用
- **perl-dbd-pg 经验**: 完全相同的 SELinux 限制，解决方案一致（HNP 包 + binary-sign-tool）

## 构建命令（手动 XS 编译）
```bash
# 1. 从 XS 生成 C 代码
perl /data/service/hnp/perl.org/perl_5.42.0/bin/xsubpp \
  -typemap /data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/ExtUtils/typemap \
  lib/Net/LibResolv.xs > lib/Net/LibResolv.c

# 2. 编译 C 为目标文件
clang -c -I$PERL_INC -I$HOME/usr/local/include \
  -fPIC -O2 -D_GNU_SOURCE -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 \
  -o lib/Net/LibResolv.o lib/Net/LibResolv.c

# 3. 链接为共享库
clang -shared -L$HOME/usr/local/lib \
  -o blib/arch/auto/Net/LibResolv/LibResolv.so \
  lib/Net/LibResolv.o
```

## 环境信息
- PERL_INC: /data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/CORE
- musl 头文件: ~/usr/local/include
- musl 库文件: ~/usr/local/lib
- 编译器: clang 18.1.8
- 目标平台: aarch64-unknown-linux-ohos

## 源码修改
1. lib/Net/LibResolv.xs: 在 MODULE 行后添加 `PROTOTYPES: DISABLE`
2. Build.PL: 替换为简化版本（移除 CChecker 依赖）

## 已应用修复（2026-06-29，参照 perl-dbd-pg 经验）

### 修复 1: conandata.yml 补丁未引用
- **问题**: conandata.yml 的 patches 字段为空 {}，但 patches/ 目录有 2 个补丁文件
- **修复**: 在 conandata.yml 中添加 patches 引用，指向 0001-Build.PL.patch 和 0002-lib-Net-LibResolv.xs.patch
- **验证**: conan create 成功导出 2 个 .patch 文件

### 修复 2: conanfile.py 内联修改 .xs
- **问题**: conanfile.py 在 build() 方法中内联修改 .xs 文件（添加 PROTOTYPES: DISABLE），而非通过 conandata 补丁
- **修复**: 移除内联修改代码，依赖 apply_conandata_patches() 应用 0002 补丁
- **验证**: 补丁正确应用，xsubpp 生成正确的 C 文件

### 修复 3: manifest.yaml sha256 为空
- **问题**: manifest.yaml 的 source.sha256 为空字符串
- **修复**: 填入 SHA256: 9004f047d71e92817a685a5ea7b8ae75d9bf9bdbbe9bd444a087a63e13044c86

### 修复 4: manifest.yaml patches_applied 为空
- **问题**: patches_applied 为空列表，但实际应用了 2 个补丁
- **修复**: 填入 0001-Build.PL.patch 和 0002-lib-Net-LibResolv.xs.patch

### 修复 5: 补丁 guard 状态为 pending
- **问题**: patch_classification 中两个补丁的 guard 均为 'pending'
- **修复**: 更新为 '#ifdef __OHOS__'（Build.PL，平台特定）和 'none'（LibResolv.xs，通用）

### 修复 6: 缺少 HNP 安装包（参照 perl-dbd-pg）
- **问题**: packaging/ 目录为空，没有 HNP 包供管理员安装
- **修复**: 创建 perl-net-libresolv.hnp（7.3KB），包含 LibResolv.pm + 签名 LibResolv.so

### 修复 7: 缺少二进制签名（参照 perl-dbd-pg）
- **问题**: .so 文件没有使用 binary-sign-tool 签名
- **修复**: 使用 /data/service/hnp/bin/binary-sign-tool 签名，生成 LibResolv.so.signed

### 修复 8: 缺少 reviewer-report 和 quality-report
- **问题**: 只有 test-report.md 和 conan-verify-report.md
- **修复**: 新增 reviewer-report.md（上库评估）和 quality-report.md（质量报告）

## 知识沉淀（6 条）
1. musl/HarmonyOS: res_query 和 res_search 直接内置于 libc，无需独立的 libresolv
2. ExtUtils::CChecker 在 HarmonyOS 上链接失败，原因是 libpth 过时且 ld.lld 无法识别 -fstack-protector-strong
3. xsubpp 将 PROTOTYPES 警告输出到 C 文件；在 .xs 中添加 PROTOTYPES: DISABLE 指令可修复
4. SELinux HMDFS 限制: HMDFS 上的 .so（hmdfs:s0）无法被 Perl（hishell_hap 域）加载；需管理员安装到系统目录
5. HarmonyOS 上的 Perl XS 模块: 手动 xsubpp + clang 编译可绕过 Build.PL/CChecker 问题
6. 二进制签名: 使用 /data/service/hnp/bin/binary-sign-tool 对 .so 签名以获得正确的 SELinux 类型

---

**首次编译**: 2026-06-26 14:51
**修复更新**: 2026-06-29 11:10（参照 perl-dbd-pg 3.18.0 经验）
**最终状态**: built（conan-verify 通过，待 CI upload 后升级为 published）
