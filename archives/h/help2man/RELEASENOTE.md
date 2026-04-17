# help2man — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf help2man-1.49.3-ohos-aarch64.tar.gz -C ~/usr/local

cd help2man-1.49.3-ohos-aarch64 && sh install-help2man-1.49.3.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.49.3 | success | 2 |

## 当前版本 (1.49.3) 详情

### 包内容
- 脚本: help2man (纯 Perl 脚本)
- 包大小: 49.5KB

### 编译信息
- 构建系统: script (纯 Perl，无需编译)
- 目标: aarch64-unknown-linux-ohos
- configure: `--prefix=$TEST_PREFIX`
- 质量门禁: PASS
- 补丁数: 2
- 测试: 手动验证 --version/--help 通过

### 补丁列表
- 0001-Makefile.patch — Makefile 修改（configure 生成的构建文件）
- 0002-help2man.patch — help2man Perl 脚本修改（嵌入正确 perl 路径）

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
