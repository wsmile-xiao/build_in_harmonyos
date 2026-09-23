# libuv 1.52.1.1 编译进度

**日期**: 2026-04-21
**状态**: ✅ 编译成功（partial）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 下载并解压源码成功 |
| Step 2 patches | ✅ | 生成 4 个补丁 |
| Step 3 configure | ✅ | cmake 配置成功 |
| Step 4 make | ✅ | 编译成功（含测试） |
| Step 5 install | ✅ | DESTDIR 安装成功 |
| Step 6 safety | ⚠️ | 跳过（库文件） |
| Step 7 check | ⚠️ | 未执行测试 |
| Step 8 staging | ✅ | 打包验证成功 |
| Step 9 package | ✅ | 生成预编译包 |
| Step 10 deploy | ✅ | 本地安装成功 |
| Step 11 finish | ✅ | 归档完成 |

## 发现与知识

### 问题 1: CPU 亲和性 API 缺失
- **错误**: `CPU_SETSIZE`, `cpu_set_t`, `sched_getaffinity`, `CPU_COUNT` 未声明
- **位置**: `src/unix/core.c` 第 1677、2055 行
- **根因**: 鸿蒙系统虽然定义 `__linux__`，但 musl libc 未实现这些 Linux 特有的 CPU 亲和性 API
- **解决**: 在 `src/unix/internal.h` 中修改 `UV__CPU_AFFINITY_SUPPORTED` 定义，排除 OHOS；在 `src/unix/core.c` 中修改条件编译，排除 OHOS

### 问题 2: mmsg API 缺失
- **错误**: `struct mmsghdr` 不完整类型，`recvmmsg`/`sendmmsg` 未声明
- **位置**: `src/unix/udp.c` 第 204、1415 行
- **根因**: 鸿蒙系统不支持 Linux 的批量消息 API（sendmmsg/recvmmsg）
- **解决**: 在 `src/unix/udp.c` 中修改条件编译，排除 OHOS 平台

### 问题 3: CMakeLists.txt 平台识别
- **错误**: CMAKE_SYSTEM_NAME 为 "HarmonyOS"，未匹配 "Linux" 条件，导致 linux.c 等文件未编译
- **根因**: libuv 的 CMakeLists.txt 只为 "Linux" 和 "Android" 编译 linux.c 等平台特定文件
- **解决**: 在 CMakeLists.txt 中修改 3 个条件，让 "HarmonyOS" 匹配 Linux 条件

### 知识提取建议
- **L1 平台真理**: OHOS 缺少 Linux CPU 亲和性 API（可写入 knowledge/operations/platform-gaps.md）
- **L1 平台真理**: OHOS 缺少 Linux mmsg API（可写入 knowledge/operations/platform-gaps.md）
- **L2 构建模式**: libuv 编译需要修改 CMakeLists.txt 添加 HarmonyOS 平台识别


## 产物信息
- 预编译包: libuv-1.52.1-ohos-aarch64.tar.gz (802KB)
- 调试符号包: libuv-1.52.1-ohos-aarch64-debug.tar.gz (81KB)
- 安装脚本: install-libuv-1.52.1.sh
- 补丁数量: 4 个

---

**编译结束**: 202
---

**编译结束**: 2026-04-30 03:01
**最终状态**: built

## OHOS 上游测试说明

独立真机验证执行上游 `uv_run_tests_a` 共 507 个用例：484 个通过、23 个跳过、0 个失败。
其中 18 个跳过由 OHOS 能力差异门控补丁 0006 引入，5 个为上游既有平台跳过；跳过项不计入通过数。
该验证结果按仓库现有平台限制案例记录，未将 SKIP 伪装为 PASS。
