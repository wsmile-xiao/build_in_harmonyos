# jo — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf jo-1.9-ohos-aarch64.tar.gz -C ~/usr/local

cd jo-1.9-ohos-aarch64 && sh install-jo-1.9.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.9 | partial | 6 |

## 当前版本 (1.9) 详情

### 包内容
- 二进制: N/A
- 包大小: 179.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-.patch-ai-review.txt.patch
- 0002-tests-jo.07.sh.patch
- 0003-tests-jo.15.sh.patch
- 0004-tests-jo.16.sh.patch
- 0005-tests-jo.24.sh.patch
- 0006-tests-jo.test.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
