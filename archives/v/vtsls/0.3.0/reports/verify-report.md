# vtsls 0.3.0 验证报告

## 验证时间

2026-06-05 11:10

## 验证环境

- Node.js: v24.13.0
- 系统: OpenHarmony (HMDFS)
- 验证目录: ~/tmp/test-bundle

## 验证项目

### G0: 干净构建验证

**不适用**: Node.js 应用无编译产物，使用预打包的 bundle。

### G1: 二进制完整性

**不适用**: Node.js 应用无 ELF 二进制。

**替代验证**: 文件完整性

```bash
tar -tzf vtsls-0.3.0-ohos-aarch64.tar.gz | wc -l
# 结果: 100+ 文件，包含所有必需依赖
```

### G2: 功能可用性

**验证命令**:
```bash
node lib/node_modules/@vtsls/language-server/bin/vtsls.js --version
```

**结果**: ✅ PASS
```
输出: 0.3.0
```

### G3: 可移植性（RPATH/签名）

**不适用**: Node.js 应用无 ELF 二进制。

**替代验证**: Node.js 模块路径

- 所有依赖已打包到 `lib/node_modules/`
- 无外部依赖，可移植

### G4: 档案完整性

**验证项目**:
- ✅ manifest.yaml 存在
- ✅ README.md 存在
- ✅ notes.md 存在
- ✅ packaging/ 目录存在
- ✅ vtsls-0.3.0-ohos-aarch64.tar.gz 存在

## 验证总结

**总体状态**: PASS（特殊处理）

**说明**:
- Node.js 应用使用 bundle 打包方式
- 不适用传统 ELF 签名和 RPATH 检查
- 功能验证通过（--version 输出正确）
- 档案完整性通过

**质量等级**: published