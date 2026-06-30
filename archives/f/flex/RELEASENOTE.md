# flex — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf flex-2.6.4-ohos-aarch64.tar.gz -C ~/usr/local

cd flex-2.6.4-ohos-aarch64 && sh install-flex-2.6.4.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.6.4 | partial | 9 |

## 当前版本 (2.6.4) 详情

### 包内容
- 二进制: N/A
- 包大小: 647.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-po-Makefile.in.patch
- 0002-src-stage1scan.c.patch
- 0003-tests-alloc_extra.c.patch
- 0004-tests-array_nr.c.patch
- 0005-tests-array_r.c.patch
- 0006-tests-basic_nr.c.patch
- 0007-tests-basic_r.c.patch
- 0008-tests-bison_nr_parser.c.patch
- 0009-tests-bison_nr_scanner.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
