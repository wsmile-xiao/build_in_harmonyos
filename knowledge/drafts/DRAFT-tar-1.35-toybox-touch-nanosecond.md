# DRAFT-tar-1.35-toybox-touch-nanosecond

## 问题
OHOS 设备唯一 touch 为 toybox 0.8.12（/usr/bin/touch -> ../../bin/toybox），不支持纳秒精度
日期参数。上游测试 `touch -d '1970-01-01T00:00:00.0000000001'` 失败：
`touch: bad date 1970-01-01T00:00:00.0000000001`（exit 1）；秒精度 `-d '...:01'` 正常（exit 0）。

## 根因
- toybox touch 对纳秒精度时间戳解析失败（bad date）
- GNU coreutils touch（支持纳秒）在设备上不存在
- 上游 time01 类测试用纳秒 touch 设置边界 mtime

## 方案
1. 安装 GNU coreutils touch（或等价纳秒精度 touch），PATH 前端实测版本后重跑受影响入口（恢复条件）
2. 无安装通道时用真实命令证明（touch 枚举 + 纳秒/秒对照实测），如实记录工具阻塞

## 验证
- `ls -la /usr/bin/touch` → toybox 0.8.12 符号链接
- `/usr/bin/touch -d '1970-01-01T00:00:00.0000000001' t1` → "bad date" exit 1
- `/usr/bin/touch -d '2038-01-19T03:14:07.0000000001' t2` → "bad date" exit 1
- `/usr/bin/touch -d '1970-01-01T00:00:01' t3` → OK exit 0（秒精度正常）
- `./testsuite 155`（time01）→ FAILED（logs/41-touch-v7-recovery-attempt.log）

## 适用边界 / 反例
- 适用：依赖纳秒 touch 设置 mtime 的上游测试在 OHOS 执行端
- 反例：秒精度 touch 正常；有 GNU coreutils 的执行端不触发

## 查重差异
- 四范围 0 命中；E010 为 toybox sed/expr（弱相关不同工具）
- 七轴：exact/causal/trigger/solution 均否，combination/boundary/test_migration 均新增

## 关系
similar_to=E010（toybox 工具链族）/ caused_by=OHOS toybox 替代 GNU coreutils /
prerequisite_of=(无) / conflicts_with=(无)

来源：tar 1.35 R02（task tar-1.35-r02-pc3-13-20260913T113300Z, pc3-13）
