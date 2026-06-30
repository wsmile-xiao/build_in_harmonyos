# basedpyright

基于 pyright 的 Python 类型检查器，提供更强大的类型推断和错误检测功能。

## 描述

basedpyright 是 pyright 的一个分支，增加了以下特性：
- 更严格的类型检查
- 更好的错误消息
- 支持更多 Python 类型特性
- 改进的代码补全

## 安装方式

基于 Node.js 的 npm 包安装：
```bash
npm install -g basedpyright
```

## 使用

```bash
# 检查 Python 文件类型
basedpyright <file.py>

# 检查整个项目
basedpyright <project-dir>
```

## 依赖

- nodejs >= 18.0.0

## 版本历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.39.6 | published | 2026-06-05 | npm 安装成功 |

## 特殊说明

basedpyright 是 Node.js 包，不适合使用传统 C/C++ 编译流程。
建议使用 npm 安装，依赖系统预装的 nodejs。
