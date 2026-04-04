# pkg-config 0.29.2 — 编译进度

> 档案创建时间: 2026-04-04
> 完成时间: 2026-04-04

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | pkg-config |
| 版本 | 0.29.2 |
| 状态 | ✅ 已完成 |
| 构建系统 | autotools |
| 源码路径 | https://pkg-config.freedesktop.org/releases/pkg-config-0.29.2.tar.gz |

## 编译阶段

### Phase 1: 环境准备
- [x] 环境检查完成
- [x] 源码下载完成
- [x] config.sub/config.guess 更新（支持 ohos 三元组）

### Phase 2: 编译过程
- [x] 配置完成（显式三元组 + --with-internal-glib）
- [x] 编译完成（需移除 glib -Werror 标志）
- [x] 安装完成（硬链接用 cp 替代）

### Phase 3: 测试验证
- [x] 功能测试（pkg-config --version → 0.29.2）
- [x] 链接验证（ELF NEEDED: 仅 libc.so）

### Phase 4: 归档收尾
- [x] 知识提取
- [x] 预编译包制作（10步流程）
- [x] 档案归档

## 发现与知识

### 问题1：config.guess 无法识别 HarmonyOS
**现象**: `configure: error: cannot guess build type; you must specify one`
**原因**: HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，不在 config.guess 数据库中
**解决**: 显式指定 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --target=aarch64-unknown-linux-ohos`
**影响范围**: 所有 autotools 项目在鸿蒙上都需要此参数

### 问题2：内部 GLib 编译失败（gatomic.c 类型错误）
**现象**: `error: incompatible integer to pointer conversion passing 'gsize' to 'gpointer'`
**原因**: glib 2.38.2 的 gatomic.c 使用整数调用需要指针的宏，clang 15 严格类型检查
**解决**: 在 glib/glib/Makefile 中添加 `-Wno-int-conversion -Wno-incompatible-pointer-types` 到 `GLIB_WARN_CFLAGS`
**注意**: 同时需移除所有 `-Werror=*` 标志，否则 `-Wno-*` 不生效

### 问题3：install-exec-hook 硬链接失败
**现象**: `ln: cannot create hard link: Operation not permitted`
**原因**: 鸿蒙 SELinux/Hmmac 限制硬链接创建
**解决**: 用 `cp` 替代硬链接创建别名二进制

## 预编译包信息

| 项目 | 值 |
|------|-----|
| 主包 | `prebuild_packages/pkg-config-0.29.2-ohos-aarch64.tar.gz` (1.4M) |
| Debug 包 | `prebuild_packages/pkg-config-0.29.2-ohos-aarch64-debug.tar.gz` (236K) |
| 文件数 | 6 |
| 外部依赖 | 无（仅 musl libc） |
| RPATH | `$ORIGIN/../lib:$ORIGIN/../lib/external` |

---

## 编译结束

- **结束时间**: 2026-04-04 18:09:47
- **最终状态**: ✅ 编译成功
- **关闭操作**: 由 close-archive.sh 执行

