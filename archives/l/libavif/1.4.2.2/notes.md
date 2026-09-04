# libavif 1.4.2.2 编译笔记（HarmonyOS PC · Conan CMake）

## 版本冲突修复
- 平台 CI L0j 检测到制品仓已有不同配方的 `libavif/1.4.2`（Build 42156）。
- 依照 R37 保留上游 v1.4.2 源码，递增配方版本至 `1.4.2.2`；`1.4.2.1` 已有远端 recipe，故不复用。

## 定位
- 产出动态 liblibavif.so，供 dlopen 及作依赖。

## 依赖边界
- 仅声明 `libdav1d/1.5.4`，其 Conan target 为 `dav1d::dav1d`。
- 上游 `AVIF_BUILD_APPS`/`AVIF_BUILD_TESTS` 关闭时，JPEG/PNG/Zlib 只服务于 app/test，不进入库目标，故不声明为依赖。
- AOM 保持 OFF；没有把 AV1 编解码核心作为新导入任务。

## CMake 选项
- `AVIF_CODEC_DAV1D=SYSTEM`
- `AVIF_LIBYUV=OFF`
- `AVIF_BUILD_APPS=OFF`
- `AVIF_BUILD_TESTS=ON`（GTest 保持 OFF，执行 `aviftest` 与 `avifyuv` 基础测试）
- `AVIF_BUILD_EXAMPLES=OFF`
- `AVIF_BUILD_MAN_PAGES=OFF`

## 签名工具边界
- 目标机没有 `/data/service/hnp/bin/binary-sign-tool`，但 task-owned `/storage/Users/currentUser/usr/local/bin` 提供 `binary-sign-tool` 与 `llvm-objcopy`。
- recipe 按 compiler conf、PATH、compiler 目录、用户本地 bin、系统 fallback 解析工具；缺失时 fail-closed，不写共享系统目录。详见知识草稿 `E2174-draft-A7F3`。

## 验证状态
- r5 目标 W3 在 `10.62.195.15:8022` 通过：Conan create RC=0，上游 CTest `3/3`，Conan test_package `7/7` 断言。
- r5 证据目录：`F:\\HarmonyPC\\libavif-1.4.2.2-w3-r5-20260903\\evidence`；远端 cleanup-only 已确认根目录不存在。
- r1-r4 的失败回执保留在各自 successor 目录，不能与 r5 结果拼接。
