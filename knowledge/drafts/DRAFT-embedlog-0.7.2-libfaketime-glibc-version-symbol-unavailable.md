# DRAFT-embedlog-0.7.2: libfaketime (LD_PRELOAD 时间伪造) 在 OHOS/musl 无法构建——date_rotate 类上游测试的环境限制

## 触发场景

embedlog 0.7.2 适配（2026-09-25，OHOS aarch64）：`make check` 共 30885
条 TAP 断言，其中 6 条 `file_date_rotate_seconds/minute/hour/day/month/year`
失败，全部属于 tst/test-el-file.c 的日期轮转测试。

## 症状签名

```
test_wrapper 内容: LD_PRELOAD=/usr/lib64/libfaketime.so FAKETIME_NO_CACHE=1 TZ=UTC ./test
not ok 30857 - file_date_rotate_seconds
# assert [test-el-file.c:2062] file_date_rotate_seconds, file_check(...log.2000-01-01--00-00-00, s1) != ok
#   return: -1, errno: 9
```

测试源（tst/test-el-file.c:2040+）用 `setenv("FAKETIME", "2000-01-01 00:00:00", 1)`
推进时间并断言轮转文件名 `log.2000-01-01--00-00-00` 等——这些只对
LD_PRELOAD 注入的 libfaketime 生效。

## 根因

1. OHOS 无 libfaketime：`/usr/lib64/libfaketime.so` 不存在；ohpcd 制品仓
   无 `faketime/*` 配方（`conan list` 实测 0 命中）
2. **源码无法在 OHOS 上构建**：wolfcw/libfaketime v0.9.13 用 `.symver`
   声明 GLIBC 符号版本（`sem_clockwait@GLIBC_2.30`/`@@GLIBC_2.34`、
   `timer_gettime@GLIBC_2.2` 等）+ `--version-script=libfaketime.map`；
   OHOS libc 为 musl 系、无 GLIBC 符号版本表，`ld.lld` 报
   `symbol pthread_cond_timedwait@@ has undefined version` 与
   `timer_gettime@GLIBC_2.2 has undefined version` 链接失败
3. FAKETIME 环境变量无人消费 → 测试按真实时钟运行 → 轮转文件名
   与期望不符（EBADF）

证据（命令 + 退出码）：
- `ls -la /usr/lib64/libfaketime.so` → No such file
- `conan list "faketime/*" -r=ohpcd` → Found 0 recipes
- `make -C src CC=clang`（libfaketime 源码树）→ ld.lld 符号版本错误，exit 1

## 归属

环境/测试工具链限制，非当前库缺陷：4 个 `no_access` 断言是 HMDFS chmod
不生效（E046 已覆盖），6 个 `date_rotate` 断言是 libfaketime 不可用（本条目）。

## 影响面与计数口径

- 计入上游测试总分母，不计通过：`30874/30885 = 99.96%`
- 恢复条件：OHOS 提供等效 LD_PRELOAD 时间伪造库，或上游测试改用
  可移植时钟注入后，恢复 test_wrapper 重跑 6 个 date_rotate 断言

## 适用边界与反例

- 适用：任何上游测试套件用 `LD_PRELOAD=libfaketime` + `FAKETIME` env 做
  日期/时间敏感断言（日志轮转、时区、定时器）
- 反例：依赖真实时钟的测试不受影响；用 `TZ=` 仅改时区的测试不受影响
  （不依赖 LD_PRELOAD）；CMake `ctest` 中无需伪造时钟的日期测试不受影响

## 与既有知识关系

- `similar_to`: E046（HMDFS chmod 不生效 → 平台限制类测试失败）
- `caused_by`: OHOS musl libc 无 GLIBC 符号版本表（E020/E026 musl/glibc 兼容族）
- 未命中任何既有条目（faketime/libfaketime 全库无覆盖）
