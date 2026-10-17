# git-flow 1.12.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Shell 脚本项目）
- 编译日期: 2026-05-27
- 编译器: 无（纯脚本）
- 状态: published

## 编译步骤

git-flow 是纯 Shell 脚本项目，无需 configure 和 make 编译步骤，直接安装即可。

### 1. 安装到 Staging 目录
```bash
# E098 解决方案：手动安装（cp + chmod 替代 install 命令）
source .build-context-git-flow-1.12.3
cd $BUILD_SRC_DIR

# 创建目录
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/share/doc/gitflow/hooks

# 安装可执行文件（755 权限）
cp git-flow $TEST_PREFIX$DEFAULT_PREFIX/bin/
chmod 755 $TEST_PREFIX$DEFAULT_PREFIX/bin/git-flow

# 安装脚本文件（644 权限）
for file in git-flow-init git-flow-feature git-flow-bugfix git-flow-hotfix \
            git-flow-release git-flow-support git-flow-version git-flow-log \
            git-flow-config gitflow-common gitflow-shFlags; do
    cp "$file" $TEST_PREFIX$DEFAULT_PREFIX/bin/
    chmod 644 $TEST_PREFIX$DEFAULT_PREFIX/bin/$file
done

# 安装 hook 文件（644 权限）
cp hooks/* $TEST_PREFIX$DEFAULT_PREFIX/share/doc/gitflow/hooks/
chmod 644 $TEST_PREFIX$DEFAULT_PREFIX/share/doc/gitflow/hooks/*
```

### 2. 本地安装（模拟用户部署）
```bash
# 同样使用手动安装方式
mkdir -p $DEFAULT_PREFIX/bin
mkdir -p $DEFAULT_PREFIX/share/doc/gitflow/hooks

cp git-flow $DEFAULT_PREFIX/bin/
chmod 755 $DEFAULT_PREFIX/bin/git-flow

# ... 其他文件同上
```

### 3. 用户验证
```bash
git flow version
# 输出: 1.12.3 (AVH Edition)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E098 | make install 失败："install: No such file or directory" | 鸟蒙系统 toybox 不包含 install 命令 | 用 cp + chmod 手动替代 install 命令 |

**详细说明**：
- 鸟蒙系统使用 toybox 提供基础命令，toybox 不包含 install 命令
- Makefile 中使用 `install -d -m 0755` 和 `install -m 0755/0644` 命令安装文件
- 解决方案：手动创建目录并使用 `cp + chmod` 替代 install 命令
- git-flow 是纯脚本，install 命令的本质是 cp + chmod，无需 strip

## 源码修改

无补丁文件。源码无需修改，仅调整安装方式（手动安装替代 make install）。

## 依赖版本

git-flow 是纯 Shell 脚本，依赖：
- git（运行时依赖，已安装）
- sh（#!/bin/sh shebang，系统自带）

## 验证结果

```bash
# Staging 验证
$TEST_PREFIX$DEFAULT_PREFIX/bin/git-flow version
1.12.3 (AVH Edition)

# 本地验证
$DEFAULT_PREFIX/bin/git-flow version
1.12.3 (AVH Edition)

# 文件完整性
- 12 个脚本文件已安装到 bin/
- 43 个 hook 文件已安装到 share/doc/gitflow/hooks/
```

## 交付物

预编译包：`git-flow-1.12.3-ohos-aarch64.tar.gz`
- 包含 bin/ 目录（12 个脚本文件）
- 包含 share/doc/gitflow/hooks/ 目录（43 个 hook 文件）
- 无 ELF 二进制，无需签名
- 纯脚本，跨平台兼容

## 注意事项

1. **E098 适配**：所有使用 install 命令的 Makefile 都需要用 cp + chmod 替代
2. **权限设置**：
   - git-flow 主脚本需要 755（可执行）
   - 其他子脚本需要 644（被 git-flow source 调用）
3. **DESTDIR 模式**：git-flow Makefile 不支持 DESTDIR，需要手动构造路径
4. **shebang 检查**：所有脚本使用 `#!/bin/sh`，兼容性好
---

**编译结束**: 2026-07-15 15:49
**最终状态**: built
