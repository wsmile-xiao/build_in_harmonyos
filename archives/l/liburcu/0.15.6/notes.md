# liburcu 0.15.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

1. `init-build liburcu 0.15.6 --url=https://lttng.org/files/urcu/userspace-rcu-0.15.6.tar.bz2`
2. patch config.guess（添加 HarmonyOS/OHOS 分支）、config.sub（添加 linux-ohos）、configure（umask 077→022）
3. `./configure --prefix=/ --enable-static --disable-shared`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. 单元测试：`cd tests/unit && make check` → 636 total, 632 PASS, 4 SKIP, 0 FAIL

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: unable to guess system type | config.guess 不含 HarmonyOS 检测分支，uname -s 返回 "HarmonyOS" | 添加 HarmonyOS/OHOS case 到 config.guess（E007） |
| 2 | config.sub: Invalid configuration ohos | config.sub 未识别 ohos 合法 OS | 添加 ohos* 到 OS 列表 + linux-ohos* 到 kernel-OS 校验（E072） |
| 3 | config.status: Permission denied (confXXXXXX) | HMDFS/SELinux 下 umask 077 创建的临时目录不可写 | patch configure 中 umask 077→022（E011） |
| 4 | 上游 make check TOTAL:0 | 顶层 make check 的 tests/regression/TESTS= 为空，测试通过递归调用 | 单元测试 `cd tests/unit && make check` 可独立运行 |

## 源码修改

- `config/config.guess`：添加 HarmonyOS/OHOS 分支（3 行）
- `config/config.sub`：ohos* 加入 OS 合法性列表 + linux-ohos* 加入 kernel-OS 校验（2 处修改）
- `configure`：umask 077→022（2 处修改）

## 依赖版本

无三方库依赖，仅需 pthread。

## 验证结果

```bash
# conan create 验证通过
conan create archives/l/liburcu/0.15.6 --build=missing -pr:h=ohos-aarch64

# 单元测试
cd tests/unit && make check
# TOTAL: 636, PASS: 632, SKIP: 4, FAIL: 0

# test_package
# test_liburcu: PASSED (rcu_read_lock/rcu_dereference/synchronize_rcu)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liburcu.a | 7 个 .a | urcu/urcu-bp/urcu-cds/urcu-common/urcu-mb/urcu-memb/urcu-qsbr |
| liburcu.pc 等 | 7 个 .pc | pkg-config 文件 |

## 注意事项

- 4 个 SKIP 为 Linux 特有测试（get_cpu_mask_from_sysfs 读取 /proc/sys/...），OHOS 无此路径
- 回归测试（rcutorture TAP）依赖 bash/tap-driver.sh，OHOS 环境未集成
- 默认静态链接，非系统同名库

---

**编译结束**: 2026-09-04 02:03
**最终状态**: built
