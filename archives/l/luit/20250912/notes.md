# luit 20250912 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build luit 20250912 --url=https://invisible-mirror.net/archives/luit/luit-20250912.tgz
2. 更新 config.guess/config.sub 为最新 GNU 版本（2026-05-17）
3. 在 config.guess 中添加 HarmonyOS 支持（`Ironclad|Linux|GNU|GNU/*|HarmonyOS` + `aarch64:HarmonyOS:*:*` pattern）
4. 修补 config.status 中 umask 077 → umask 022（HMDFS 不允许 umask 077 创建的目录内写文件）
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1`
7. `make install DESTDIR=$TEST_PREFIX` (staging)
8. 安全弹窗验证(R7): `luit -V` → `luit - 2.0-20250912`
9. `make check` → 无批量测试
10. `ohc-run.py package luit 20250912`
11. `make install` (无 DESTDIR, 安装到 $DEFAULT_PREFIX)
12. 用户验证: `$DEFAULT_PREFIX/bin/luit -V` → `luit - 2.0-20250912`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config scripts 不包含 HarmonyOS | 更新 config.guess/config.sub + 手动添加 HarmonyOS case |
| 2 | config.status 无法创建临时文件 | HMDFS 上 umask 077 创建的目录无法写入 | 将 config.status 中 umask 077 改为 umask 022 |
| 3 | G4 档案完整性检查失败 | manifest.yaml 缺少 build_system 字段 | 在 manifest.yaml 顶部添加 build_system: autotools |

## 源码修改

- config.guess: 更新为 GNU 最新版(2026-05-17) + 添加 HarmonyOS 支持
  - 第153行: `Ironclad|Linux|GNU|GNU/*|HarmonyOS)` (添加 HarmonyOS 到 LIBC 检测)
  - 第988行前: 添加 `aarch64:HarmonyOS:*:*) GUESS=$UNAME_MACHINE-unknown-linux-musl ;;`
- config.sub: 更新为 GNU 最新版(2026-05-17)（已支持 linux-musl）
- config.status: umask 077 → umask 022（运行时修改，不持久化为补丁）

## 依赖版本

- zlib (系统自带, configure 自动检测)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/luit -V
# 输出: luit - 2.0-20250912
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| luit-20250912-ohos-aarch64.tar.gz | 197KB | 预编译包 |
| luit-20250912-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- luit 不支持 --version，使用 -V 查看版本
- HMDFS 上 umask 077 创建的目录无法写入文件，需要使用 umask 022
- config.guess/config.sub 需要手动添加 HarmonyOS 支持（GNU 最新版仍不包含）

**编译结束**: 2026-06-15
**最终状态**: published
---

**编译结束**: 2026-06-15 15:02
**最终状态**: published
