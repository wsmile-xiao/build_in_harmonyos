# 编译过程记录模板
<!-- 放置路径: archives/{letter}/{name}/{version}/reports/build-report.md -->

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | {软件名} |
| 版本 | {版本号} |
| 编译日期 | {YYYY-MM-DD} |
| 编译者 | {编译者} |

## 环境信息

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang {版本} |
| 构建系统 | {autotools/cmake/meson/etc} |

## 编译过程

### 1. 源码获取

```bash
# 下载源码
wget {下载链接}
tar -xzf {源码包}
cd {源码目录}
```

### 2. 配置

```bash
# 配置命令
./configure --prefix=$HOME/usr/local {配置选项}

# 或 CMake
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local ..
```

**配置输出关键信息**：
```
{粘贴关键配置输出}
```

### 3. 编译

```bash
make -j$(nproc)
```

**编译耗时**: {X分钟}

**编译警告/错误**：
```
{记录重要的警告或错误}
```

### 4. 安装

```bash
make install
```

**安装文件列表**：
```
{列出安装的关键文件}
```

## 遇到的问题

### 问题1: {问题描述}

**现象**：
```
{错误信息}
```

**原因分析**：
{分析原因}

**解决方案**：
```bash
{解决步骤}
```

## 验证测试

```bash
# 基本功能验证
{验证命令}
```

## 总结

{编译经验总结}