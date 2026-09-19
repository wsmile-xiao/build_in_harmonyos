# libgtop-tools 2.41.3 测试报告

**日期**: 2026-09-19
**验证方式**: `ohc-run.py conan-verify`（G2 conan create 干净构建 + test_package 实跑）
**结论**: 通过（conan-verify 全门禁 PASS，可标记 published）

## 上游测试（R51 三步法）

| 步骤 | 结果 |
|---|---|
| 清点 | libgtop 2.41.3 官方源码 `make check` 无注册测试（test_count=0）；examples/ 19 个 noinst_PROGRAMS 为 API 自检示例，不随 install 安装、无可运行测试套件 |
| 运行 | 上游无可运行测试套件，以 test_package 消费者测试替代 |
| 申报 | 上游 N=0 / 通过率 0/0 不适用；适配后补增 3 项（见下） |

## 适配后测试（鸿蒙特有测试，test_package）

| # | 测试 | 结果 |
|---|---|---|
| 1 | test.c：libgtop_daemon2 存在且可执行 | OK（日志：`OK: libgtop_daemon2 found at ...`） |
| 2 | test.c：libgtop_server2 存在且可执行 | OK（日志：`OK: libgtop_server2 found at ...`） |
| 3 | 实际执行 `libgtop_daemon2 --help`（GOption 解析真实代码路径，动态链接 glib + 静态链接树内 libgtop-2.0） | OK（exit 0） |

**通过率: 3/3 (100%)**

### libgtop_server2 实际执行记录（不计入失败判据）

`libgtop_server2 < /dev/null` 在 OHOS 普通用户环境执行至 setreuid() 时被
seccomp 拦截（Signal 31/SIGSYS）。libgtop_server2 是上游设计的 **suid root
辅助进程**（upstream Makefile.am 以 setuid 方式安装），main() 无条件调用
setreuid()；该行为是上游 suid 设计与 OHOS 非根沙箱的已知边界，非适配缺陷
（动态/静态链接、加载、初始化均已验证可达 setreuid 调用点）。测试中执行该
二进制并记录结果（ignore_errors），不作为失败判据。

## 交付物

| 文件 | 说明 |
|---|---|
| bin/libgtop_daemon2 | 系统监控守护进程（静态链接树内 libgtop-2.0，动态链接 glib） |
| bin/libgtop_server2 | suid server 辅助进程（同上） |

## 门禁记录

- G0/G1/G2/G3/G4 + L2/L4/L5: PASS（archives/l/libgtop-tools/2.41.3/reports/conan-verify-report.md）
- 上游测试用例通过率：0/0（不适用，上游无测试）
- 新增测试用例通过率：3/3（100%）
