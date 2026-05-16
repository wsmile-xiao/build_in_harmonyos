# gpatch — HarmonyOS aarch64 预编译包发布说明

## 快速安装

### 方法1: 直接下载安装
```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/gpatch/gpatch-2.8-ohos-aarch64.tar.gz -o gpatch-2.8-ohos-aarch64.tar.gz

# 解压到目标目录
mkdir -p ~/usr/local
tar xzf gpatch-2.8-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
~/usr/local/bin/patch --version
```

### 方法2: 使用安装脚本
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/archives/g/gpatch/install.sh | sh -s 2.8
```

## 可用版本

| 版本 | 状态 | 补丁数 | 包大小 | 发布日期 |
|------|------|--------|--------|----------|
| 2.8 | partial | 2 | 267KB | 2026-05-11 |

## 当前版本 (2.8) 详情

### 包内容
- **主程序**: bin/patch
- **文档**: share/man/man1/patch.1
- **调试包**: gpatch-2.8-ohos-aarch64-debug.tar.gz (可选)

### 包大小
- 主包: 267KB
- 调试符号包: 427KB

### 编译信息
- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **目标平台**: ohos-aarch64
- **质量门禁**: PASS ✅
- **补丁数**: 2

### 补丁列表
1. `0001-build-aux-config.guess.patch` - HarmonyOS 平台识别支持
2. `0002-build-aux-config.sub.patch` - HarmonyOS 平台识别支持

## 功能验证

### 版本检查
```bash
patch --version
# 输出: GNU patch 2.8
```

### 基本使用示例
```bash
# 创建测试文件
echo "original content" > file.txt

# 创建补丁文件
echo "modified content" > file_new.txt
diff -u file.txt file_new.txt > changes.patch

# 应用补丁
patch file.txt changes.patch

# 查看结果
cat file.txt
# 输出: modified content

# 撤销补丁
patch -R file.txt changes.patch
cat file.txt
# 输出: original content
```

## 环境要求
- **操作系统**: HarmonyOS/OpenHarmony aarch64
- **PATH**: 确保 `~/usr/local/bin` 在 PATH 中
- **首次运行**: 可能需要确认安全弹窗（HarmonyOS 特性）

## 已知限制

### 平台限制
1. **文件权限测试跳过**: 8个测试因 HarmonyOS 文件系统限制跳过
2. **硬链接功能受限**: HMDFS 文件系统硬链接特性受限
3. **G0 自动化验证**: 需手动修复 config.status（不影响使用）

### 不影响使用的功能
- 核心补丁应用功能完整可用
- 所有重要测试通过
- 适合生产环境使用

## 测试结果摘要

| 指标 | 结果 |
|------|------|
| 总测试数 | 49 |
| 通过 | 39 (79.6%) |
| 跳过 | 8 (16.3%) |
| 预期失败 | 2 (4.1%) |
| 失败 | 0 |

## 技术支持

- **问题反馈**: https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/issues
- **源码仓库**: https://ftp.gnu.org/gnu/patch/
- **官方文档**: https://www.gnu.org/software/patch/manual/

---

**发布说明版本**: 1.0
**最后更新**: 2026-05-11