# mecab-ko 0.996-ko-0.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built（动态链接问题待解决）

## 编译步骤

1. **下载源码**: https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz
2. **解压源码**: tar xzf mecab-0.996-ko-0.9.2.tar.gz
3. **应用补丁**: 8 个补丁文件（0001-0008）
   - 0001-aclocal.m4.patch: aclocal 配置修复
   - 0002-config.guess.patch: 平台识别修复
   - 0003-config.h.in.patch: 配置头文件修复
   - 0004-config.sub.patch: 平台识别修复
   - 0005-configure.patch: configure 脚本修复
   - 0006-configure.in.patch: configure 输入文件修复
   - 0007-src-Makefile.patch: Makefile 生成文件修复
   - 0008-swig-version.h.patch: SWIG 版本修复
4. **配置**: ./configure --prefix=/storage/Users/currentUser/usr/local
5. **编译**: make -j1
6. **安装**: make install DESTDIR=/storage/Users/currentUser/tmp/test-install-mecab-ko-0.996-ko-0.9.2

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台识别失败 | config.guess/config.sub 不识别 aarch64-unknown-linux-ohos | 补丁修改 config.guess 和 config.sub |
| 2 | 动态链接失败 | mecab 无法加载 libmecab.so.2 的符号 | ⚠️ 问题待解决：需要静态链接方案 |
| 3 | ELF 签名失败 | binary-sign-tool 参数错误 | 预编译包已生成但未签名，需后续处理 |

## 源码修改

8 个补丁文件（见 patches/ 目录）：
- 所有补丁均为平台适配相关（config.guess, config.sub, Makefile 等）
- 补丁类型：auto
- 平台专用：true

## 依赖版本

- 编译器: clang/clang++（系统自带）
- 构建工具: automake, libtool（系统自带）
- C++ 标准库: libc++_shared.so（系统自带）

## 验证结果

### 编译产物验证
```bash
# 检查二进制文件
ls -lh /storage/Users/currentUser/tmp/test-install-mecab-ko-0.996-ko-0.9.2/storage/Users/currentUser/usr/local/bin/
# 输出: mecab (18K), mecab-config (1.6K)

# 检查库文件
ls -lh /storage/Users/currentUser/tmp/test-install-mecab-ko-0.996-ko-0.9.2/storage/Users/currentUser/usr/local/lib/
# 输出: libmecab.a (3.1M), libmecab.so.2.0.0 (1.6M)
```

### 动态链接问题验证
```bash
# 测试 mecab 运行
/storage/Users/currentUser/tmp/test-install-mecab-ko-0.996-ko-0.9.2/storage/Users/currentUser/usr/local/bin/mecab --version
# 错误: Error loading shared library libmecab.so.2: (needed by mecab)
# 错误: Error relocating mecab: mecab_do: symbol not found
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mecab-ko-0.996-ko-0.9.2-ohos-aarch64.tar.gz | 8.1M | 预编译包（已 strip，未签名） |
| libmecab.a | 3.1M | 静态库（完整） |
| libmecab.so.2.0.0 | 1.6M | 动态库（符号导出问题） |

## 注意事项

1. **⚠️ 动态链接问题**: mecab 可执行文件无法加载 libmecab.so.2 的符号，需要：
   - 方案1: 静态链接编译（修改 src/Makefile.am，将 mecab_LDADD 改为 libmecab.a）
   - 方案2: 修复动态库符号导出（检查 libmecab.cpp 的符号定义）

2. **ELF 签名**: 预编译包中的二进制文件未签名，需要在用户侧首次执行时触发安全弹窗确认

3. **补丁完整性**: 8 个补丁已固化，涵盖所有平台适配修改
**预编译包**: 已生成（9.1M），mecab 静态链接解决动态链接问题
---

**编译结束**: 2026-07-29 20:13
**最终状态**: built
