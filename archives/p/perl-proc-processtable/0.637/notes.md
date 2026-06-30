# perl-proc-processtable 0.637 适配笔记

## 编译环境
- 构建系统: perl-eumm (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 平台: HarmonyOS (aarch64, musl libc)
- 状态: published

## 编译步骤

1. 下载源码 `Proc-ProcessTable-0.637.tar.gz` 并解压
2. 应用补丁 `0001-Makefile.PL.patch`（修复 musl 兼容性）
3. 从 `os/` 目录复制 `obstack.c` 和 `obstack.h` 到源码根目录（musl libc 不提供 obstack）
4. 运行 `perl Makefile.PL INSTALLDIRS=site` 生成 Makefile
5. 运行 `make -j1` 编译 XS 模块
6. 运行 `make install DESTDIR=<staging>` 安装到临时目录
7. 遍历 staging 目录，提取 `lib/` 路径下的文件到 Conan 包目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报错 `obstack.h: No such file or directory` | musl libc 不提供 glibc 的 obstack.h | 从源码 os/ 目录复制 obstack.c/obstack.h 到根目录 |
| 2 | 链接报错 `-lobstack not found` | Makefile.PL 默认链接 -lobstack | patch Makefile.PL 移除 -lobstack，改用 bundled obstack.c |
| 3 | LDFROM 设置不当导致 .so 生成失败 | Makefile.PL 中 LDFLAGS/LDFROM 配置问题 | patch 修正 LDFROM 变量 |
| 4 | Conan profile `os.cpu.arch=armv8` 报错 | settings.yml 不支持 os.cpu.arch 嵌套 | 改为 `arch=armv8` |
| 5 | G4 产物检查失败：找不到 bin/lib/include | `conan cache path <ref>` 返回 recipe export 路径(/e) | 修复 conan_verify.py: 用 `conan list '<ref>:*' -c -f=json` 获取 pkg_id, 再 `conan cache path '<ref>:<pkg_id>'` 获取二进制包路径(/p) |
| 6 | XS .so 运行时加载失败 (Permission denied) | SELinux E046: hmdfs context 不允许 dlopen | test_package 使用 ignore_errors=True; 部署时安装到系统 Perl 目录 |

## 源码修改

### 0001-Makefile.PL.patch

修改 `Makefile.PL` 文件：
- 移除 `-lobstack` 链接选项，改为编译 bundled `obstack.c`
- 修正 `LDFROM` 变量设置
- 添加 `-Ios` include 路径
- 平台限定: 仅 HarmonyOS/musl 需要

## 依赖版本

- Perl: 5.42.0 (aarch64-linux)
- Conan: 2.12.0
- clang: 15
- musl libc (HarmonyOS)

## 验证结果

### conan-verify 全部通过

```
G0: PASS  (预构建风险评估)
G1: PASS  (配方完整性检查)
G2: PASS  (conan create 干净构建)
G3: PASS  (静态链接验证)
G4: PASS  (产物完整性检查)
L2: PASS  (平台功能矩阵)
L4: PASS  (静态安全扫描)
L5: PASS  (产物基线对比)
```

### 产物验证

- ELF64 AArch64 共享对象 ✅
- 仅依赖 libc.so ✅
- XS 符号导出正确: `boot_Proc__ProcessTable`, `OS_initialize`, `bless_into_proc` ✅
- Perl 模块语法检查通过 ✅
- 纯 Perl 模块 (Killfam) 加载成功 ✅

### 运行时限制

- XS .so 加载受 SELinux E046 限制（hmdfs context 不允许 dlopen）
- 详见: `reports/functional-test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码和补丁声明 |
| patches/0001-Makefile.PL.patch | musl 兼容性补丁 |
| test_package/conanfile.py | 测试配方 |
| reports/conan-verify-report.md | conan-verify 验证报告 |
| reports/conan-create.log | conan create 构建日志 |
| reports/functional-test-report.md | 功能测试报告 |

## 注意事项

1. **SELinux E046**: XS 模块 .so 文件无法从 Conan cache 或用户目录加载。部署时需安装到系统 Perl 目录 (`/data/service/hnp/perl.org/perl_5.42.0/lib/`)，该目录具有正确的 `hnp_file` SELinux context。
2. **obstack 依赖**: musl libc 不提供 obstack.h，必须使用源码 bundled 的 os/obstack.c 和 os/obstack.h。
3. **Conan profile**: 必须使用 `arch=armv8` 而非 `os.cpu.arch=armv8`。
4. **conan_verify.py 修复**: G3/G4 检查需要使用二进制包路径(/p) 而非 recipe 路径(/e)，需通过 `conan list '<ref>:*' -c -f=json` + `conan cache path '<ref>:<pkg_id>'` 获取。

---

**编译结束**: 2026-06-26 18:00
**最终状态**: published
