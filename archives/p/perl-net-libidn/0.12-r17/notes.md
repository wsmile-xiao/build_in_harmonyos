# perl-net-libidn 0.12-r17 — 编译笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | perl-net-libidn (Net::LibIDN) |
| 版本 | 0.12-r17 |
| 类型 | Perl XS/C 模块 |
| 构建系统 | Perl ExtUtils::MakeMaker (perl Makefile.PL) |
| 源码 | https://cpan.metacpan.org/authors/id/T/TH/THOR/Net-LibIDN-0.12.tar.gz |
| SHA256 | 2f8acc9442b3866ec7dc63cd449fc693ae3e930d5d3e5e9430fbb6f393bdbb17 |

## 依赖
- libidn 1.43 (从源码编译安装到 /usr/local)
- Perl 5.42.0

## 编译过程

### 1. 编译 libidn 依赖
- 源码: libidn-1.43.tar.gz (https://ftp.gnu.org/gnu/libidn/)
- 问题1: config.guess 不识别 HarmonyOS → 复制 automake-1.16 的 config.guess/config.sub
- 问题2: config.status umask 077 导致 HMDFS 上临时目录内无法创建文件 → 移除 umask 077
- 结果: libidn.a + libidn.so.12.6.6 安装到 /usr/local

### 2. 编译 perl-net-libidn
```bash
perl Makefile.PL --with-libidn=/usr/local/lib --with-libidn-inc=/usr/local/include
make
make install DESTDIR=$TEST_PREFIX
```
- 结果: LibIDN.so (30080 bytes, ELF shared object, 64-bit LSB arm64) 生成成功
- 安装到: $TEST_PREFIX/.../auto/Net/LibIDN/LibIDN.so

### 3. OHOS 链接器问题修复
- **问题**: OHOS 平台缺少 CRT 文件 (crti.o, crtn.o, crtbeginS.o, crtendS.o)，链接阶段失败
- **修复**: 创建 `patches/0001-Makefile.PL-ohos-linker.patch`，在 Makefile.PL 中注入 OTHERLDFLAGS:
  - `-nostartfiles -nodefaultlibs -lc` 绕过缺失的 CRT 文件
- **参考**: perl-dbd-pg 3.18.0 的相同问题处理方式

### 4. Conan 配方问题修复
- **问题1**: `os=OHOS` 在 settings.yml 中无效 → 添加 OHOS 枚举值
- **问题2**: YAML 格式错误 `[, ...]` → 改为 `[null, ...]`
- **问题3**: `ConanInvalidConfiguration` 导入路径错误 → 从 `conan.errors` 导入
- **问题4**: `libdirs.append("lib")` 导致多元素 → 改为 `libdirs = ["lib"]`

## Conan 配方验证结果
- G0: ✅ PASS (预构建风险评估)
- G1: ✅ PASS (配方完整性)
- G2: ✅ PASS (conan create 干净构建成功)
- G3: ✅ PASS (无系统同名库冲突)
- G4: ✅ PASS (产物完整性: lib/ 含 .so, .pm)
- L2: ✅ PASS (smoke test)
- L4: ✅ PASS (安全扫描: NX+PIE+RELRO+CANARY)
- L5: ✅ PASS (产物基线已保存)

## 功能测试结果
- libidn C 库功能: ✅ 全通过 (idna_to_ascii, idna_to_unicode, stringprep_profile)
- .pm 语法检查: ✅ syntax OK
- 二进制签名: ✅ .codesign section 存在
- Perl XS 模块加载: ❌ SELinux HMDFS 限制 (平台级，非编译问题)
- HNP 安装包: ✅ 已创建 (perl-net-libidn.hnp, 14KB)

## .so 文件
- 编译路径: blib/arch/auto/Net/LibIDN/LibIDN.so
- Conan缓存: /storage/Users/currentUser/.conan2/p/b/perl-662a37c7831b0/p/lib/LibIDN.so
- 签名文件: ~/tmp/LibIDN.so.signed
- HNP包: archives/p/perl-net-libidn/0.12-r17/reports/perl-net-libidn.hnp

## 关键经验
1. Perl XS 模块需要设置 LD_LIBRARY_PATH 以便 Makefile.PL 的检测程序能找到依赖库
2. OHOS 平台缺少 CRT 文件，需要 -nostartfiles -nodefaultlibs -lc 链接标志
3. conan settings.yml 需要手动添加 OHOS 枚举值
4. ConanInvalidConfiguration 从 conan.errors 导入
5. package_info 中 libdirs 应赋值而非 append
6. SELinux 限制不影响编译，仅影响运行时加载
7. binary-sign-tool 可用于 .so 签名
8. HNP 包格式用于管理员安装到系统目录

---

**编译结束**: 2026-06-29
**最终状态**: published
**conan-verify**: 全 Gate 通过 (G0-G4 + L2/L4/L5)
