# gpatch 2.8 — OpenHarmony 编译记录

## 基本信息
- **软件**: gpatch (GNU patch)
- **版本**: 2.8
- **构建系统**: autotools
- **目标平台**: ohos-aarch64
- **编译日期**: 2026-05-11
- **编译状态**: partial

## 编译配置
- **prefix**: `/storage/Users/currentUser/usr/local`
- **configure选项**: `--prefix=/storage/Users/currentUser/usr/local`

## 补丁清单
| 补丁文件 | 类型 | 说明 |
|---------|------|------|
| 0001-build-aux-config.guess.patch | 平台适配 | 添加 HarmonyOS 平台识别支持 |
| 0002-build-aux-config.sub.patch | 平台适配 | 添加 HarmonyOS 平台识别支持 |

## 编译步骤
1. 解压源码包
2. 应用补丁（更新 config.guess 和 config.sub）
3. 运行 configure
4. 运行 make
5. 运行 make install DESTDIR（staging安装）
6. 运行 make check（测试验证）
7. 本地安装验证
8. 打包预编译包

## 测试结果
- **总测试数**: 49
- **通过**: 39 (79.6%)
- **跳过**: 8 (16.3%)
- **预期失败**: 2
- **失败**: 0
- **状态**: 通过 ✅

详细测试报告见 `reports/test-report.md`

## 已知限制
### 平台限制
1. **HMDFS 文件系统限制**: 
   - mktemp 创建的临时目录权限异常（2700/drwx--S---）
   - 需手动修复 config.status 临时目录创建逻辑
   
2. **跳过的测试**:
   - 文件权限和硬链接相关测试因平台限制跳过
   - 不影响核心功能使用

### 编译注意事项
⚠️ configure 运行后，需手动修改 config.status 文件第590-601行，将：
```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` && test -d "$tmp"
```
替换为：
```sh
tmp=./conftmp$$
rm -rf "$tmp"
mkdir "$tmp" && chmod 755 "$tmp"
```

## 预编译包
- `gpatch-2.8-ohos-aarch64.tar.gz` - 主包 (267KB)
- `gpatch-2.8-ohos-aarch64-debug.tar.gz` - 调试符号包
- `install-gpatch-2.8.sh` - 安装脚本

## 功能验证
```bash
# 验证安装
/storage/Users/currentUser/usr/local/bin/patch --version
# 输出: GNU patch 2.8

# 基本使用测试
echo "test" > file1.txt
cp file1.txt file2.txt
echo "test modified" > file2.txt
diff -u file1.txt file2.txt > test.patch
patch file1.txt test.patch
cat file1.txt
# 输出: test modified
```

---
编译者: OpenHarmony Compile Agent
最后更新: 2026-05-11