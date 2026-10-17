# libocxl 1.2.1 — HarmonyOS PC 适配说明

## 概况

libocxl 是 OpenCAPI 加速卡的用户态驱动库：打开 AFU（`/dev/ocxl/...`）、attach 上下文、
映射 MMIO、分配 IRQ、读写 AFU MMIO。

- 上游：https://github.com/OpenPOWERFoundation/libocxl （源码取自 Debian orig tarball）
- 形态：库（`libocxl.so.1`/`libocxl.a` + `src/include/libocxl.h`）
- 许可证：Apache-2.0
- 依赖：无；构建需内核 uapi 头 `misc/ocxl.h`（随包提供）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游只有手写 Makefile | 直接用 OHOS clang 编译 5 个源文件；保持上游 flags（`-I src/include -I kernel/include -fPIC -D_FILE_OFFSET_BITS=64 -DLIBOCXL_SUPPRESS_INACCESSIBLE_WARNINGS`） |
| 2 | Makefile 构建时下载 uapi 头 | `source()` 取 pinned 副本（Linux v6.12 `include/uapi/misc/ocxl.h`，sha256 固定）到 `kernel/include/misc/`，可复现且离线 |
| 3 | `src/libocxl_info.h` 由 perl 生成 | `build()` 用 `version.pl` 生成，传入 `VERSION_MAJOR/MINOR/PATCH=1.2.1` 与 `CC` |
| 4 | 版本脚本 | 共享库用 `-Wl,-soname,libocxl.so.1 -Wl,--version-script,symver.map`（lld 支持 version-script） |

## 测试

### 上游

上游单测 `unittests/unittests.c` 依赖 `unittests/virtocxl.c`——一个用 **FUSE** 把目录
挂载成虚拟 `/dev/ocxl` 设备的程序，`make test` 以 `sudo` 运行、链接 `-lfuse -lpthread`。
OHOS 用户态不提供 FUSE，**未运行**（技术原因）。`test_package/MANIFEST.yml` 已声明。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_libocxl.c` 共 9 条断言，覆盖硬件无关 API：

- `ocxl_err_to_string`：`OCXL_OK`→"OK"、`OCXL_NO_MEM`→"No memory"、
  `OCXL_INVALID_ARGS`→"Invalid arguments"、未知值→"Unknown error"
- `ocxl_enable_messages`/`ocxl_set_error_message_handler` 可调用
- `ocxl_info()` 非空且含 `LibOCXL Version: 1.2.1`
- `ocxl_afu_open_from_dev("/nonexistent")` 与 `ocxl_afu_open("no-such-afu")` 均失败并保持 `afu == NULL`

## 已知限制

- AFU open/attach、MMIO、IRQ 等真正访问硬件的路径无法在无 OpenCAPI 加速卡的环境验证。
- `OCXL_NO_DEV` 在 `ocxl_err_to_string` 中落到 `default`（返回 "Unknown error"），这是上游行为。
- 上游 `ocxl_set_error_message_handler(NULL)` 不做判空：若同时 `ocxl_enable_messages(OCXL_ERRORS)`，
  错误路径会调用 NULL 函数指针（SIGSEGV）。消费者测试改用无害的 handler，规避该上游缺陷。
