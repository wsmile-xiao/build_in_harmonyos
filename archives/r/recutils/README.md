# recutils

GNU Recutils是一套工具和库，用于访问称为recfiles的人类可编辑的文本数据库。

## 基本信息

- **版本**: 1.9
- **构建系统**: autotools
- **编译日期**: 2026-05-27
- **状态**: built

## 简介

Recutils提供了一套命令行工具（recinf, recsel, recins等）和C库，用于创建、查询和操作recfiles格式的数据库文件。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 1.9 | built | ❌ | 2 |

## OHOS 适配要点

### HMDFS 权限问题
- configure 在HMDFS上创建临时文件失败（Permission denied）
- 解决方案：设置 TMPDIR=/storage/Users/currentUser/tmp/build-tmp
- 原因：HMDFS 文件系统的特殊权限限制

### configure 检测问题
- 未设置TMPDIR时，configure检测closedir失败
- 导致 HAVE_CLOSEDIR=0，触发Windows代码路径编译失败

## 依赖

无外部依赖

## 功能验证

```bash
recinf --version
# 输出: recinf (GNU recutils) 1.9
```

## 参考

- 官网: https://www.gnu.org/software/recutils/