# lzo2 2.10 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build lzo2 2.10 --url=https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz
```

### 2. 平台适配（关键步骤）
遇到 config.guess 无法识别 HarmonyOS 系统的问题（E007），执行以下修改：

**修改 1: 更新 config.guess 和 config.sub**
```bash
# 使用 SKILL 内置的补丁脚本
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl autoconf/config.guess autoconf/config.sub
```
- 添加 __OHOS__ LIBC 检测
- 添加 HarmonyOS 系统识别
- 输出三元组: aarch64-unknown-linux-ohos

**修改 2: configure 脚本 umask 问题**
HMDFS 文件系统对 `umask 077` 有权限限制，修改 configure 脚本：
```bash
# 将 umask 077 改为 umask 022
sed -i 's/umask 077/umask 022/g' configure
```

### 3. 编译
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-lzo2-2.10
make check
```

### 4. 测试
执行 `make check` 测试所有 37 个压缩算法，全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS/__OHOS__ 检测分支 | 使用 patch-autotools-ohos.pl 打补丁 |
| 2 | configure 创建临时目录权限拒绝 | HMDFS 文件系统对 umask 077 有特殊限制 | 将 configure 中 umask 077 改为 022 |

## 源码修改

### 补丁文件清单
使用 track-edit 记录修改：
- autoconf/config.guess (E007: 平台识别)
- autoconf/config.sub (E007: 三元组支持)
- configure (HMDFS umask 适配)

### 修改类型标注
- autoconf/config.guess: 构建系统文件（无需 __OHOS__ 守卫）
- autoconf/config.sub: 构建系统文件（无需 __OHOS__ 守卫）
- configure: 构建系统文件（无需 __OHOS__ 守卫）

## 依赖版本

无外部依赖，lzo2 是独立的压缩库。

## 验证结果

### 编译验证
```bash
./configure --prefix=$DEFAULT_PREFIX
# 输出: aarch64-unknown-linux-ohos
make -j1
# 成功编译静态库 liblzo2.a
make check
# All checks passed
```

### 功能验证
- 37 个压缩算法全部测试通过
- 压缩/解压缩功能正常
- 最佳压缩率: 43.4% (LZO1X-999)

## 交付物

| 文件 | 说明 |
|------|------|
| liblzo2.a | 静态库 |
| lzo2.pc | pkg-config 文件 |
| include/lzo/*.h | 头文件 |
| lzo2-2.10-ohos-aarch64.tar.gz | 预编译包 |

## 注意事项

1. **必须应用 E007 补丁**：所有 autotools 项目在 HarmonyOS 上编译都需要修改 config.guess/config.sub
2. **umask 问题**：HMDFS 文件系统需要使用 umask 022，不能使用 077
3. **静态库编译**：lzo2 默认编译为静态库（--disable-shared），适合嵌入式系统

## 知识提取

### 关键知识
- E007: config.guess 无法识别 HarmonyOS 系统（已应用）
- HMDFS umask 限制（新发现，需要记录）
---

**编译结束**: 2026-05-21 13:27
**最终状态**: published
---

**编译结束**: 2026-07-15 14:41
**最终状态**: built

