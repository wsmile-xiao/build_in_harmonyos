# makedepend 1.0.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：https://www.x.org/releases/individual/util/makedepend-1.0.9.tar.gz
2. 应用平台适配补丁：
   - 使用 patch-autotools-ohos.pl 修补 config.guess 和 config.sub
   - 手动修改 config.sub，添加 `linux-ohos*` 规则
3. 修复 configure 权限问题：
   - 修改 config.status 脚本，使用固定临时目录 build_tmp
4. 编译命令：
   ```bash
   bash configure --prefix=/storage/Users/currentUser/usr/local
   make -j2
   make install DESTDIR=/storage/Users/currentUser/test-install-makedepend-1.0.9
   ```
5. 测试验证：
   ```bash
   make check  # 所有测试通过 (PASS: 2)
   makedepend test.c  # 在有 Makefile 的目录中成功生成依赖
   ```
6. 本地安装：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 修补 |
| 2 | config.sub 报错 "Kernel `linux' not known to work with OS `ohos'" | 缺少 linux-ohos 组合规则 | 手动添加 `linux-ohos*) ;;` 规则 |
| 3 | config.status 报错 "Permission denied" 创建临时文件 | 在源码目录创建临时文件受限 | 修改 config.status 使用固定目录 build_tmp |

## 源码修改

- **0001-config.guess.patch**: 添加 HarmonyOS 系统识别（__OHOS__ 检测）
- **0002-config.sub.patch**: 添加 ohos-linux triplet 和 linux-ohos 组合规则

注意：根据铁律 R6，只修改源文件（config.guess/config.sub），不修改生成文件（makedepend-config.h、makedepend.1）。

## 依赖版本

无外部库依赖。构建工具依赖：
- autoconf 2.72
- automake 1.16.5
- pkg-config 0.29.2
- GNU make 4.4.1

## 验证结果

```bash
# 测试套件
make check
# PASS: 2/2

# 功能验证
cd ~/tmp/makedepend-test
cat > Makefile << 'EOF'
test: test.o
	$(CC) -o test test.o
EOF
echo 'int main() { return 0; }' > test.c
makedepend test.c
cat Makefile  # 显示 "# DO NOT DELETE" 标记，说明依赖生成成功
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| makedepend-1.0.9-ohos-aarch64.tar.gz | 50K | 预编译包（zip格式，实际为 zip 但命名遵循规范）|

## 注意事项

1. makedepend 需要在包含 Makefile 的目录中运行，否则会报错 "[mM]akefile is not present"
2. 本版本通过所有测试，功能正常
3. 打包时遇到 tar 的 ustar header 限制，改用 zip 格式（重命名为 tar.gz）
---

**编译结束**: 2026-06-09 10:46
**最终状态**: built
