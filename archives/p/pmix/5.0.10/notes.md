# pmix 5.0.10 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-05-29}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---
**编译开始**: 2026-05-29 12:00
**版本**: pmix 5.0.10
**编译系统**: autoconf/automake

## 深度绕过方案实施记录

### 问题分析
原始错误：
```
./config.status[1403]: can't create ./confCSlbzm/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根本原因**: config.status 脚本使用 `mktemp -d "./confXXXXXX"` 创建临时子目录，然后在其中创建临时文件（如 `subs1.awk`、`defines.awk`）。鸿蒙系统阻止了在临时子目录中创建文件的操作。

### 实施方案：方案 A（修改 config.status）

**核心修改**:
1. 定位临时目录创建代码（config.status 第 888-896 行）
2. 替换 `tmp=`(umask 077 && mktemp -d "./confXXXXXX")`` 为 `tmp="."`
3. 保留 `ac_tmp=$tmp`（确保后续引用正确）
4. 替换所有 `$ac_tmp/` 引用为 `./conf_`（使用当前目录的固定文件名前缀）

**修改后的效果**:
- 临时文件 `conf_subs1.awk`、`conf_subs.awk`、`conf_defines.awk` 直接在当前目录创建
- 避免了临时子目录创建操作
- config.status 成功运行，生成所有 Makefile 和配置文件

### 编译过程

#### 1. config.status 修改
```python
# 使用 Python 精确修改 config.status
- 替换第 888-895 行的临时目录创建逻辑为 tmp="."
- 保留第 896 行的 ac_tmp=$tmp
- 替换所有 $ac_tmp/ 引用为 ./conf_（21 处）
```

#### 2. config.status 执行
```bash
./config.status
# 成功输出：
# config.status: creating Makefile
# config.status: creating src/include/pmix_config.h
# config.status: creating include/pmix_version.h
# ... (共 100+ 个文件)
# config.status: executing libtool commands
```

#### 3. 编译
```bash
make -j2
# 成功编译所有模块：
# - libpmix.la（核心库）
# - pmix_mca_pcompress_zlib.la（压缩插件）
# - pevent, pmix_info, plookup, pps, pattrs, pquery（工具）
# - pmixcc（编译器 wrapper）
# - palloc, pctrl（管理工具）
# - 测试程序和示例程序
```

#### 4. 安装
```bash
make install DESTDIR=$TEST_PREFIX
# 成功安装到 staging 目录
```

#### 5. 预编译包制作
```bash
# 手动创建 tarball
cd $TEST_PREFIX/$DEFAULT_PREFIX
tar czf pmix-5.0.10-ohos-aarch64.tar.gz bin lib include share etc

# ELF 签名
ohc-run.py sign-elf pmix-5.0.10-ohos-aarch64.tar.gz

# 移动到归档目录
mv pmix-5.0.10-ohos-aarch64.tar.gz $ARCHIVE_DIR/packaging/
```

#### 6. 本地安装验证
```bash
make install  # 安装到 $DEFAULT_PREFIX
/storage/Users/currentUser/usr/local/bin/pmix_info --all
# 输出显示：
# PMIX: 5.0.10
# PMIX Standard: 5.1
# Prefix: /storage/Users/currentUser/usr/local
# ... (所有配置正确)
```

### 最终状态
✅ **编译成功**
✅ **预编译包已创建**: pmix-5.0.10-ohos-aarch64.tar.gz (15M)
✅ **本地安装验证通过**: pmix_info 可正常运行

### 技术总结
- **使用的绕过方案**: 方案 A（修改 config.status）
- **关键修改**: 替换临时目录创建逻辑 + 重定向文件引用
- **适用范围**: 所有使用 `mktemp -d` 创建临时子目录并尝试在其中创建文件的 autoconf 生成脚本
- **稳定性**: 高（直接修改 config.status，不依赖外部环境）
- **可重复性**: 高（修改可固化为补丁或脚本）

---
**编译结束**: 2026-05-29 12:10
**最终状态**: built