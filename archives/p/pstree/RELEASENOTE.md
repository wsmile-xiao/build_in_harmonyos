# pstree — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf pstree-23.7-ohos-aarch64.tar.gz -C ~/usr/local
```

## 可用版本

| 版本 | 状态 | 补丁数 | 编译方式 |
|------|------|--------|----------|
| 23.7 | success | 0 | 单文件编译 |

## 当前版本 (23.7) 详情

### 包内容
- 二进制: `bin/pstree`
- 包大小: 142KB（未 strip）

### 编译信息
- 构建系统: 单文件编译
- 编译器: clang
- 目标: aarch64-unknown-linux-ohos
- 依赖: ncursesw (静态链接)
- 质量状态: 成功

### 特殊说明
- 从 psmisc 仓库单独编译 pstree.c
- 手动定义 VERSION 宏
- 使用 libncursesw.a（带宽字符支持）

### 功能验证
```bash
$ pstree --version
pstree (PSmisc) 23.7
Copyright (C) 1993-2024 Werner Almesberger and Craig Small
```

### 已知限制
- 仅包含 pstree 工具
- 不包含 psmisc 的其他工具（killall, fuser, peekfd）

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- musl libc (ld-musl-aarch64.so.1)
- ncursesw 库（已预装）