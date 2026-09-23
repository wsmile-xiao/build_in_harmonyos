# fftw 3.3.11 适配笔记

## 当前状态

- 上游稳定版本：3.3.11
- 源码归档：`https://www.fftw.org/fftw-3.3.11.tar.gz`
- 构建系统：CMake
- 外部 Conan 依赖：无；运行时仅链接系统 `libm`
- 本地 `conan create`：Windows/MinGW formal Conan R5 通过（exit 0）。

## 适配变更

- CMake 上游文件将 `FFTW_VERSION` 更新为 3.3.11。
- CMake 目标属性修正为 `SOVERSION 3`、`VERSION 3.11.10`，保持 ABI 主版本并避免把版本字段倒置。
- `CLOCK_SGI_CYCLE` 返回错误时回退到 `CLOCK_MONOTONIC`，避免 OHOS 运行时 `EINVAL` 导致计时循环无进展。
- 关闭 OpenMP、threads、Fortran、long-double 和上游 CTest；测试包仍执行真实 DFT、正逆变换和 r2c 数值断言。

## 验证记录

- 官方下载页显示 FFTW 3.3.11；归档大小 4,310,712 字节，SHA-256 为
  `5630c24cdeb33b131612f7eb4b1a9934234754f9f388ff8617458d0be6f239a1`。
- 两个源码改动补丁由 `refresh-patch --auto` 在 WSL 路径下生成，均已对原始 3.3.11 源码 dry-run 通过。
- 目标 W3-008 已完成：目标功能、AArch64 ELF/SONAME/NEEDED/.codesign 回读、上游 CTest 2/2、消费者测试均通过；唯一 launch_count=1。
- Windows formal Conan 生成包引用：`fftw/3.3.11#dda26601697d40c3eb769520fee38cc4:02a4fa5ac7f5235a6610247fd7c8e6877972277b#e6f037c7cf0d3eb0f50274be01cfd14b`。

## 安全边界

- 只使用官方 3.3.11 归档和哈希；3.3.10 的任务/制品记录不作为当前版本证据。
- 当前 manifest 标记为 `built`，表示本地 Conan 与目标验证已完成但尚未执行合并后的 `/release`；不得把本地包缓存或 W3 结果解释为制品仓已发布。
