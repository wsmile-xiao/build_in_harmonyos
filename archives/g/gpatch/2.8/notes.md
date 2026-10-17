# gpatch 2.8 适配笔记

## 基本信息
- 软件: GNU patch
- 版本: 2.8
- 构建系统: autotools
- 上游: https://ftp.gnu.org/gnu/patch/patch-2.8.tar.xz
- 许可证: GPL-3.0-or-later

## 问题与解决方案

### 问题1: config.guess 无法识别 HarmonyOS (E007)
- 现象: configure 阶段报错 "config.guess: unable to guess system type"
- 原因: 上游 config.guess/config.sub 不包含 HarmonyOS 识别
- 解决: 替换为支持 HarmonyOS 的版本，生成 0001/0002 补丁
- 知识图谱: E007

### 问题2: config.status 临时目录权限异常 (E011)
- 现象: HMDFS 文件系统上 mktemp 创建的临时目录权限为 2700/drwx--S---，导致 configure 二次运行时无法在临时目录中创建文件
- 原因: configure 脚本使用 `umask 077` 创建临时目录
- 解决: conanfile.py generate() 中将 configure 的 `umask 077` 改为 `umask 022`
- 知识图谱: E011

### 问题3: make check 部分测试跳过
- 跳过测试: 8个文件系统相关测试 (file-create-modes, file-modes, hardlinks 等)
- 原因: HarmonyOS 文件系统权限和硬链接限制
- 影响: 不影响核心补丁功能

## 验证命令
```bash
# 版本验证
patch --version
# 输出: GNU patch 2.8

# 基本补丁应用测试
echo "original" > file.txt
echo "modified" > file_new.txt
diff -u file.txt file_new.txt > changes.patch
patch file.txt < changes.patch
cat file.txt  # 输出: modified

# 撤销补丁
patch -R file.txt < changes.patch
cat file.txt  # 输出: original
```
