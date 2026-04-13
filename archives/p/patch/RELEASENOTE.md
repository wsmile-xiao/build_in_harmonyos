# GNU patch — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf patch-2.7.6-ohos-aarch64.tar.gz -C ~/usr/local
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试 |
|------|------|--------|------|
| 2.7.6 | partial | 2 | 32/44 PASS |

## 当前版本 (2.7.6) 详情

### 包内容
- 二进制: `bin/patch`
- 包大小: 188KB（已 strip + ELF 签名）

### 编译信息
- 构建系统: autotools
- 编译器: clang
- 目标: aarch64-unknown-linux-ohos
- configure 参数: `--prefix=$HOME/usr/local`
- 质量门禁: PASS (G1-G4)

### 补丁列表
1. `0001-config-guess-harmonyos-support.patch` — config.guess 添加 HarmonyOS 系统识别 (E007)
2. `0002-config-sub-harmonyos-support.patch` — config.sub 添加 ohos 三元组验证 (E072)

### 测试结果
- **32 PASS** / 9 FAIL / 1 SKIP / 2 XFAIL
- 失败项均为鸿蒙平台兼容性问题（umask 差异、SELinux 软链接限制、shell 行为差异）
- **核心补丁功能已验证可用**：apply / reverse / dry-run / unified diff / context diff

### 已知限制
- 文件权限相关测试受鸿蒙 umask 默认值影响
- SELinux 限制导致软链接测试失败
- libattr 不可用，xattr 功能缺失

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- musl libc (ld-musl-aarch64.so.1)
