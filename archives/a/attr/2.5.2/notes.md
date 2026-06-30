# attr 2.5.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. **init-build**: 下载 tarball 并解压到 .orig/.work 双目录
2. **config.guess/config.sub 补丁**: 使用 `patch-autotools-ohos.pl` 添加 HarmonyOS 识别
3. **config.sub 补充修复**: 手动添加 `linux-ohos*` 到 kernel-os 白名单 (E072)
4. **configure umask 补丁**: 修改 configure 脚本中 `umask 077` → `umask 022` (HMDFS 兼容)
5. **configure**: `./configure --prefix=$DEFAULT_PREFIX`
6. **make**: `make -j1` (使用 ACLOCAL=true 绕过 automake 缺失)
7. **make install**: `make install DESTDIR=$TEST_PREFIX`
8. **make check**: 执行测试 (2/2 FAIL - 平台限制)
9. **conan-init/conan-verify**: 生成并验证 Conan 配方 (8 道门禁全部 PASS)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 无 OHOS 检测分支 (E007) | `patch-autotools-ohos.pl` 补丁 |
| 2 | config.sub 拒绝 aarch64-unknown-linux-ohos | kernel-os 白名单缺少 linux-ohos* (E072) | 手动添加 `linux-ohos*` 到 case $kernel-$os |
| 3 | config.status 创建临时文件失败 (Permission denied) | HMDFS 上 umask 077 创建 700 权限目录，UID 映射导致无法访问 | 修改 configure 中 umask 077 → 022 |
| 4 | make 触发 aclocal-1.16 失败 | automake 未安装，时间戳触发重生成 | `ACLOCAL=true AUTOMAKE=true make` |
| 5 | test/run 脚本无法执行 | `#!/usr/bin/perl` 路径不存在，perl 在 /data/service/hnp/bin/perl | 修改 test/run shebang |
| 6 | make check 测试失败 (2/2) | HarmonyOS 不完全支持 user xattr，getfattr 无法读取；Signal 31 (SIGSYS) 未实现 syscall | 平台限制，记录为已知限制 |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| build-aux/config.guess | 0001 | 添加 HarmonyOS 系统识别 |
| build-aux/config.sub | 0002 | 添加 ohos-linux 三元组 + kernel-os 白名单 |
| configure | 0003 | umask 077 → 022 (HMDFS 兼容) |
| include/config.h.in | 0004 | autoheader 生成的平台适配 |
| test/run | 0005 | perl shebang 路径修复 |

## 依赖版本

无外部依赖 (attr 是独立的扩展属性工具库)

## 验证结果

### make check 结果
```
# TOTAL: 2
# PASS:  0
# SKIP:  0
# FAIL:  2
# ERROR: 0
```

- test/attr.test: 119 commands (87 passed, 32 failed) - getfattr 无法读取 user xattr
- test/root/getfattr.test: Signal 31 (core dumped) - 未实现的 syscall (SIGSYS)

### conan-verify 结果
```
G0: 预构建风险评估 - PASS
G1: 配方完整性 - PASS
G2: conan create (干净构建) - PASS
G3: 系统同名库隔离 (R26) - PASS
G4: 产物完整性 - PASS
L2: smoke test - PASS
L4: 静态安全扫描 (checksec) - PASS
L5: 产物基线对比 - PASS
```

## 注意事项

- attr 是系统同名库 (libattr)，按 R26 使用 `--disable-shared` 静态编译
- make check 失败是平台限制，非编译问题：
  - HarmonyOS 文件系统不完全支持 user extended attributes
  - 部分 xattr 相关 syscall 未实现 (Signal 31/SIGSYS)
- configure umask 补丁是 HMDFS 特定问题，在其他文件系统上可能不需要
---

**编译结束**: 2026-06-29 15:40
**最终状态**: built
