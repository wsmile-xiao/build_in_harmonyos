# smtpping 1.1.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`PROJECT(smtpping)`）
- 编译日期: 2026-09-20
- 编译器: OHOS SDK clang/clang++ 15.0.4（aarch64-linux-ohos，profile `ohos-aarch64-device`）
- Conan: 2.29.1（OHOS 适配版），`smtpping/1.1.4@ohpcd/stable`
- 状态: built

## 编译步骤

1. `init-build` 从官方源拉取
   `https://github.com/halon/smtpping/archive/refs/tags/v1.1.4.tar.gz`
   （sha256 `beca8c44…ef74a` 校验通过；上游仓库已由 halonsecurity/smtpping
   迁移至 halon/smtpping，标签为 `v1.1.4`）。
2. 源码改动（2 个补丁，均为 OHOS 解析器 API 兼容）：
   - `0001-resolver.cpp.patch`：`res_ninit/res_nquery/res_nclose` →
     `res_query()` + 全局 `h_errno`；
   - `0002-resolver.hpp.patch`：删除 glibc 专有的 `struct __res_state` 成员，
     补 `<netdb.h>`（h_errno/NO_DATA）。
3. `conan create` 按 conanfile.py 流程执行：CMakeToolchain 注入
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 `cmake_minimum_required(VERSION 2.8)`，
   CMake ≥4.0 已移除 <3.5 兼容）→ configure/build/install。
4. `conan-verify`（G0–G4 全 PASS）→ 本地 CI 门禁 → `finish` W3 复核。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `res_ninit`/`res_nquery`/`res_nclose` 未声明、无法编译 | OHOS NDK 的 `<resolv.h>` 只声明经典 API（res_init/res_query/res_search/res_send/res_mkquery + dn_expand/dn_skipname）；OHOS libc.so 也无 `res_n*` 符号（`nm -D /system/lib64/libc.so` 实测） | 补丁改用 `res_query()` + 全局 `h_errno`（smtpping 每进程单线程，fork 并发，全局态安全；与知识条目 E516 同族问题） |
| 2 | `struct __res_state m_res` 成员不再需要 | 非重入 API 不使用调用方状态结构 | 补丁删除成员；`GetLastError()` 返回全局 `h_errno` |
| 3 | CMake 4.4.3 拒绝 `cmake_minimum_required(VERSION 2.8)` | CMake ≥4.0 移除 <3.5 policy 兼容 | 配方 `generate()` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 v1.1.5 PR #13 的同款修法，零补丁） |
| 4 | 上游 `IF (CMAKE_SYSTEM_NAME STREQUAL "Linux")` 链接 resolv 在 OHOS 不生效 | OHOS 的 CMAKE_SYSTEM_NAME 为 `OHOS` | 无需处理：OHOS 的 `res_query` 由 libc.so 导出，不需要 `-lresolv`；`-lpthread` 解析到 NDK 的 `libpthread.a` |
| 5 | HMDFS 下 make jobserver mkfifo 报 `Operation not permitted` | 平台文件系统限制（已知 E002 族） | 非阻塞：make 自动串行继续构建，产物正确 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-resolver.cpp.patch` | `resolver.cpp` | POSIX 分支：`res_nquery(&m_res, …)` → `res_query(…)`；`m_res.res_h_errno == NO_DATA` → `h_errno == NO_DATA`；构造/析构中移除 `res_ninit`/`res_nclose` |
| `0002-resolver.hpp.patch` | `resolver.hpp` | 删除 `struct __res_state m_res;` 成员；`GetLastError()` 返回全局 `h_errno`；`#else` 分支补 `#include <netdb.h>` |

补丁中不含任何平台宏（无 `__OHOS__`）、无绝对路径、无环境变量注入。

## 依赖版本

无第三方依赖（仅 libc/libc++：POSIX socket、getopt、semaphore、pthread）。

## 验证结果

```text
# 手工构建冒烟（设备侧，.work 源码）
smtpping -v            -> 1.1.4 (rc=0)
smtpping -h            -> Usage 输出 (rc=0)
mock SMTP 回环 E2E     -> 1 e-mail messages transmitted，各阶段 RTT 统计正常
关闭端口负路径          -> "connect() failed" + "no pings were sent" (rc=0)
localhost MX 解析路径   -> MX NO_DATA 回退 A/AAAA，解析到 127.0.0.1/::1（res_query 真机可用）
# W3 / CI 同源 conan create（设备 profile）
test_package: 15/15 assertions passed
# 本地 CI 门禁
G0/KC/JC/L0/L1/L4/L5 PASS（见 reports/w3-local-ci.log）
```

## 注意事项

- 补丁将解析器从 glibc 重入 API 改为进程全局态。smtpping 的并发模型是
  `fork()`（`-P` 选项），不是线程，因此不存在数据竞争；上游 `-P` 下每个
  子进程各自持有独立副本。
- `dn_expand` 在 OHOS libc 中是弱符号（`W`），实测运行正常。
- 上游 1.1.5 已修复 CMake policy 与解析器健壮性问题，但本任务版本为 1.1.4，
  适配以最小补丁保持行为等价。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/smtpping` | 命令行工具（SMTP 延迟/吞吐测量） |
| `man/man1/smtpping.1` | 上游 man 手册（cmake install 默认安装） |
| `licenses/LICENSE` | GPL-2.0-or-later 许可证 |
| `packaging/smtpping-1.1.4-ohos-aarch64.tar.gz` | Conan 包产物发布归档 |

**编译结束**: 2026-09-20 —— W3/CI 本地门禁全过（消费者测试 15/15）。
---

**编译结束**: 2026-09-20 21:24
**最终状态**: built
