# bison — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf bison-3.8.2-ohos-aarch64.tar.gz -C ~/usr/local

cd bison-3.8.2-ohos-aarch64 && sh install-bison-3.8.2.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.8.2 | partial | 5 |

## 当前版本 (3.8.2) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.6MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-doc-bison.1.patch
- 0004-doc-stamp-vti.patch
- 0005-doc-version.texi.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
