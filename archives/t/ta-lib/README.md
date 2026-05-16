# ta-lib — OpenHarmony 编译记录

## 软件信息
- **名称**: ta-lib (Technical Analysis Library)
- **功能**: 金融市场技术分析库，提供158个技术指标函数
- **官网**: https://ta-lib.org
- **源码**: https://github.com/ta-lib/ta-lib

## 编译版本
| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|----------|----------|
| 0.6.4 | ✅ 成功 | autotools | 2026-05-09 |

## 编译指导

### 前置依赖
- 无特殊依赖，标准 C 编译环境即可

### 配置参数
```bash
./configure --prefix=$DEFAULT_PREFIX
```

### 编译命令
```bash
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX  # staging 安装
make install                        # 本地安装
```

### 关键补丁
1. **config.guess**: 添加 HarmonyOS 识别
2. **config.sub**: 更新以支持 HarmonyOS
3. **configure**: 移除 umask 077（解决 HMDFS 临时目录权限问题）
4. **configure.ac**: 简化配置

## 补丁清单
| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-config.guess.patch | platform | 添加 HarmonyOS 识别分支 |
| 0002-config.sub.patch | platform | 更新以支持 HarmonyOS |
| 0003-configure.patch | platform | 移除 umask 077 限制 |

## 已知限制
- Code profiling 不支持此平台（非阻塞警告）
- HMDFS 文件系统：使用 `$TMPDIR` 而非 `/tmp`

## 功能验证

### 测试命令
```bash
# 回归测试
LD_LIBRARY_PATH=./src/.libs ./src/tools/ta_regtest/.libs/ta_regtest
```

### 测试结果 (v0.6.4)
- **状态**: PASS
- **覆盖**: 158个技术指标全部通过
- 包括：移动平均线、RSI、MACD、布林带、蜡烛图形态等

## API 使用示例
```c
#include <ta-lib/ta_libc.h>

TA_RetCode retCode;
double closePrice[] = {1.0, 2.0, 3.0, 4.0, 5.0};
double outReal[5];
int outBegIdx;
int outNBElement;

retCode = TA_SMA(0, 4, closePrice, 3, &outBegIdx, &outNBElement, outReal);
```

## 归档文件
```
archives/t/ta-lib/0.6.4/
├── manifest.yaml       # 元数据
├── PROGRESS.md         # 编译进度
├── README.md           # 本文件
├── RELEASENOTE.md      # 发布说明
├── install.sh          # 安装脚本
├── patches/            # 补丁文件
├── reports/            # 测试报告
│   └── test-report.md
└── packaging/          # 预编译包
    └ ta-lib-0.6.4-ohos-aarch64.tar.gz
```

## 相关知识
- E007: config.guess 平台识别问题
- E046: HMDFS 临时目录权限问题
- R20: DESTDIR 模式
- R10: 使用 $TMPDIR 而非 /tmp
