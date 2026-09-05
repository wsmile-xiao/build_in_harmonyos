# E430 — OHOS librt 空壳，无 POSIX mqueue（mqueue 类测试须配置排除）

## 错误特征
依赖 POSIX mqueue 的测试用例在 OHOS 上无法运行：
```
FAIL: case-10-mqueue
FAIL: case-20-mqueue-endpoint
FAIL: mq_fork
FAIL: mq_open
```
或运行时报 `mq_open: Function not implemented`（ENOSYS，errno 38）。
检查库文件：
```
ls -la <sysroot>/usr/lib/librt.a   # 约 8 字节空壳归档
```

## 触发条件
- 构建系统: autotools（TESTS/check_PROGRAMS 声明 mqueue 用例）
- 阶段: make check / testing
- 平台: OHOS
- 上游测试套件包含 POSIX mqueue（mq_open/mq_send/mq_receive）用例时

## 根因分析
OHOS libc 的 librt 为空壳（librt.a 实测约 8 字节），未提供 POSIX mqueue
实现（mq_* 系列 ENOSYS 或链接期即不可用）。上游为 Linux 完整 libc 设计的
mqueue 测试用例在 OHOS 上不可运行，属平台能力缺口而非移植缺陷。

## 解决方案

### 推荐方案
make check 命令行层排除（不改上游测试源码）：
```bash
# autotools：用 TESTS 变量覆盖排除 mqueue 用例
make check TESTS="$(ls tests/*.test | grep -v mqueue | tr '\n' ' ')"
# 或在 check_PROGRAMS/TEST_EXTENSIONS 层面做变量覆盖
```
并在 PR 测试统计中如实声明排除原因（平台缺口），不得静默丢弃。

### 禁止做法
- ❌ 修改上游测试源码删除用例（应保持命令行/配置层适配）
- ❌ 静默跳过不声明（测试统计必须如实反映排除项及原因）
- ❌ 试图桩实现 mq_* 函数伪造测试通过

## 验证
```bash
# 确认 librt 空壳
ar t <sysroot>/usr/lib/librt.a
# 确认排除后 make check 其余用例正常运行
make check TESTS="..." # 排除 mqueue 后应无 ENOSYS 类 FAIL
```

## 关联条目
- 相关: E429（fdinfo 方向位缺口，同为内核/libc 级平台数据缺口）、E201（/bin/bash 缺失的测试执行适配）
