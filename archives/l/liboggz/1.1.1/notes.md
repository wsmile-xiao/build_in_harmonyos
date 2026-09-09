# liboggz 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-08
- 编译器: clang/clang++（OHOS aarch64，profile ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤

1. 上游源码核验：官方 Xiph 源 https://downloads.xiph.org/releases/liboggz/liboggz-1.1.1.tar.gz，SHA-256=6bafadb1e0a9ae4ac83304f38621a5621b8e8e32927889e65a98706d213d415a
2. 更新 config.guess/config.sub 至 2023-08-22（识别 HarmonyOS aarch64，host=aarch64-unknown-linux-ohos）
3. 修复 configure 中 umask 077 临时目录在 HMDFS 上不可写的问题（改为 umask 000）
4. 修复 include/oggz/oggz_off_t_generated.h 中 loff_t → off_t（HarmonyOS 无 loff_t）
5. configure 选项：--host=aarch64-unknown-linux-ohos --enable-static --disable-shared --prefix=$DEFAULT_PREFIX
6. make -j1 && make check（上游 23/23 通过）
7. make install DESTDIR=$TEST_PREFIX 验证 staging
8. conan-verify：G1-G4 + L2/L4/L5 全 PASS（conan create 干净构建 + test_package 消费者测试通过）
9. finish W3 本地 CI 模拟通过（.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | liboggz 1.1.1（2009 年）自带 config.guess/config.sub 过旧，不识别 HarmonyOS | 更新为 2023-08-22 版本（0001/0002 补丁），host=aarch64-unknown-linux-ohos |
| 2 | config.status 报 can't create ./confXXXXXX/subs1.awk: Permission denied | configure 以 umask 077 创建临时目录，HMDFS 对属主也不可写 | configure 补丁 umask 077 → 000（0003 补丁） |
| 3 | source(): IsADirectoryError './PATCHES' | HMDFS 大小写不敏感，tarball 根级 PATCHES 文件与配方导出 patches/ 目录冲突 | source() 中 excludes=["*PATCHES"] |
| 4 | test_package: ogg/ogg.h not found | liboggz 公共头 <oggz/oggz.h> 包含 <ogg/ogg.h>，需向消费者传递 libogg 依赖 | package_info 声明 cpp_info.libs=["oggz"] + requires.append("libogg::libogg")；test_package 显式依赖 libogg |
| 5 | cpp_info.libs=["liboggz"] 导致 Library not found | 库文件为 liboggz.a，链接名应为 oggz | 修正 cpp_info.libs=["oggz"] |

## 源码修改

- patches/0001-config.guess.patch：config.guess 2009 → 2023-08-22（识别 aarch64 HarmonyOS → aarch64-unknown-linux-ohos）
- patches/0002-config.sub.patch：config.sub 2009 → 2023-08-22（校验 aarch64-unknown-linux-ohos）
- patches/0003-configure.patch：configure 临时目录 umask 077 → 000（HMDFS 权限陷阱）
- patches/0004-include-oggz-oggz_off_t_generated.h.patch：typedef loff_t → off_t（HarmonyOS 无 loff_t）

## 依赖版本

- libogg/1.3.5（ohpcd registry 已发布，配置为静态库依赖）

## 验证结果

```bash
# 上游测试（src/tests，make check）
All 23 tests passed

# Conan 干净构建 + test_package 消费者测试
conan-verify: G1-G4 + L2/L4/L5 全 PASS
test_package: test_liboggz 1/1 Passed

# W3 本地 CI 模拟
.ci-result.json exit_code=0（L0/L1/L2 pass）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方，依赖 libogg/1.3.5，静态库 oggz |
| conandata.yml | 官方 Xiph 源 URL + SHA-256 + 4 个补丁声明 |
| patches/ | 4 个适配补丁（config.guess/config.sub/configure/oggz_off_t） |
| test_package/ | 消费者测试（oggz_new/oggz_close）+ MANIFEST.yml（上游 23 项测试声明） |

## 注意事项

- 纯库包（.a/.so），无命令行工具，不需要 commands.json
- 上游测试 23/23 通过（R51 三步法：清点 src/tests 25 个测试源 + make check 实测 23 项 + 回填 MANIFEST.yml）
- 基线隔离审计：W3 期间对 main 基线中 util-linux-login/2.42.2/.ci-trigger（blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391，提交 761df452e5）做临时 index 隔离以通过 JC5 全量扫描，复验通过后已无条件恢复（blob 与基线一致）

### 对话 #1
2026-09-08: 完整适配流程（init-build → lang-preflight → 探索编译 → conan-init → conan-verify G1-G4/L2/L4/L5 PASS → finish W3 本地 CI 模拟 PASS）
