# libfolia 2.21 适配笔记

## 编译环境
- 构建系统: autotools (需 autoreconf)
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化编译环境: ohc-run.py build libfolia 2.21
2. 源码无 configure，需运行 autoreconf -fi 生成
3. Configure 遇到 HMDFS 权限问题（E011）
4. 修复: `sed -i 's/umask 077/umask 022/g' configure`
5. Configure 成功通过
6. Make 成功编译
7. Make check 通过（1 个测试 PASS）
8. Package 成功生成预编译包
9. Verify-build 通过所有门禁（G1-G4）
10. 功能测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：Permission denied creating subs1.awk | HMDFS 文件系统 UID 映射导致 umask 077 创建的目录对当前进程不可写（E011） | sed -i 's/umask 077/umask 022/g' configure |
| 2 | 运行时缺少 libomp.so | folialint 使用 OpenMP 进行并行处理 | 安装 libomp 15.0.4 预编译包 |

## 源码修改

**无源码补丁**。所有修改为运行时操作：
- autoreconf -fi（生成 configure）
- sed umask 修改（运行时操作，不固化为补丁）

**原因**：
- 原始 tarball 不包含 configure/config.guess/config.sub
- 这些文件由 autoreconf 生成，不应打补丁
- umask 修改为 E011 标准解决方案，记录在 knowledge/graph/E011.kv

## 依赖版本

- libxml-2.0 >= 2.9.4 (已安装)
- ticcutils >= 0.34 (已安装)
- icu-uc >= 50, icu-io (已安装)
- libomp 15.0.4 (运行时依赖，需用户安装)

## 验证结果

```bash
folialint --version
folialint version 0.5
based on [libfolia 2.21]
```

测试结果：
```
Testsuite summary for libfolia 2.21
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
```

功能测试：
- ✅ 版本验证
- ✅ FoLiA 文档验证
- ✅ 错误检测功能
- ✅ 库文件完整性

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfolia-2.21-ohos-aarch64.tar.gz | 91 MB | 预编译包（已签名） |
| libfolia-2.21-ohos-aarch64-debug.tar.gz | 37 MB | 调试符号包 |

## 上库状态

- ✅ G1-G4 门禁通过
- ✅ 软件级 README.md 已创建
- ✅ 测试报告已生成
- ✅ 补丁合规（无生成文件补丁）

---
**编译结束**: 2026-06-05 10:29
**最终状态**: published