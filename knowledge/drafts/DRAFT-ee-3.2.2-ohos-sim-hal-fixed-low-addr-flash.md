# STM32 HAL 依赖嵌入式固件库的 OHOS 适配：模拟 HAL + 固定低地址 mmap 模拟 Flash

> 草稿编号：DRAFT-ee-3.2.2-ohos-sim-hal-fixed-low-addr-flash
> 来源事件：ee 3.2.2（NimaLTD.I-CUBE-EE，STM32 EEPROM 模拟库）HarmonyOS PC 适配，2026-09-20
> 状态：草稿待审（未 promote）

## 问题

依赖 STM32 HAL 的嵌入式固件库（如 ee 3.2.2）移植到 64 位 OHOS 宿主时同时存在三个障碍：

1. **头文件耦合**：`ee.h` 直接 `#include "main.h"`（STM32CubeMX 生成的 HAL 头），OHOS 无此头文件 → 编译失败。
2. **直接地址解引用 + 32 位地址截断**：`ee.c` 用 `uint32_t` 保存 Flash 基址，并以
   `(*(__IO uint8_t*)(eeHandle.Address + i))` 直接读写地址。64 位宿主上若缓冲区地址
   超过 4 GiB，截断后解引用 → **SIGSEGV（默认 PIE 链接必现；-no-pie 碰巧正常，掩盖问题）**。
3. **无真实 Flash 硬件**：需要可观察的模拟语义（空态 0xFF、擦除、编程 1→0、写入后读回校验），
   空壳 stub 不满足适配完整性要求（R8/R40）。

## 根因

- 嵌入式 MCU 库假定 32 位平坦地址空间 + 直接地址解引用 + HAL 头文件耦合；
- OHOS 宿主没有 STM32 Flash 硬件与 HAL；
- 64 位平台上 `uint32_t` 地址字段对真实缓冲区地址的截断。

## 方案

1. **模拟 HAL 头 `main.h`**：定义 `__IO`、`HAL_StatusTypeDef`/`HAL_OK`、
   `FLASH_EraseInitTypeDef`、`FLASH_BASE`/`FLASH_PAGE_SIZE`/`FLASH_SECTOR_SIZE`/
   `FLASH_TYPEPROGRAM_HALFWORD` 等宏；MCU 型号宏选 `STM32F7`（其分支不重定义
   `FLASH_SIZE`，避免与模拟层宏冲突）。
2. **模拟 Flash `ee_sim_flash.c`**：
   - 构造时 `mmap((void*)0x20000000UL, 16KiB, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)`
     固定映射低地址缓冲区并整段置 0xFF（Flash 空态）；
   - `HAL_FLASHEx_Erase` = `memset(0xFF)`（真实擦除语义），成功写 `PageError=0xFFFFFFFF`；
   - `HAL_FLASH_Program` = 半字写入，与 0xFF 做与运算（1→0 真实编程语义）；
   - `HAL_FLASH_Unlock/Lock` = 无操作返回 `HAL_OK`；
   - `EE_Read` 直接寻址命中该缓冲区；mmap 失败时 HAL 函数如实返回 `HAL_ERROR`（真实错误而非越界）。
   - 固定低地址是**关键**：保证 `uint32_t` 地址恒为合法低地址，与 PIE 无关。
3. **配方集成**：conanfile.py 用 `tools.build:compiler_executables` 取 clang + llvm-ar
   直接编译归档（参考 archives/m/micro-ecc 范式）；新增文件补丁必须用标准
   `--- /dev/null` + `+++ b/<file>` 头部（conan `apply_conandata_patches` 对
   `--- a/...` 双前缀新增文件补丁会报 "source/target file does not exist"）。

## 验证

- 默认 PIE 链接下 smoke_test 全绿：`EE_Capacity()=1024`、写 0xDEADBEEF… 回读一致、
  格式化后全 0xFF、NULL 参数被拒绝；
- 消费者用例（设备参数持久化服务）：重启回读恢复一致、格式化清空，仅用公开 EE_* API；
- conan-verify G2 干净构建 + finish W3 本地 CI（JC/KC/L0-L5）通过。

## 适用边界

- 适用：依赖 STM32/Cortex-M HAL 且内部以 32 位整型保存地址并直接解引用的嵌入式
  固件/中间件库；需要可观察 Flash 语义的宿主模拟场景。
- 反例/不适用：已有自身上层抽象、不直接解引用地址的库无需此模式；需要真实硬件
  外设语义（如时序、中断）的场景不能仅靠内存模拟。
- 边界：固定低地址被占用时 mmap 失败（如实报错而非越界）；窗口必须 < 4 GiB 才能
  保证 `uint32_t` 地址安全。

## 查重差异（七轴摘要）

- exact_duplicate：无；causal_duplicate：无（根因=库内地址截断，非平台 VA 上限）；
- trigger_overlap：部分（与 boxfort 39bit-VA、snmalloc mmap 同属"OHOS 上 mmap 地址选择"，触发场景不同）；
- solution_overlap：部分（都用低地址 mmap 思路，方案形态不同：模拟 Flash vs 探测回退/禁 mitigation）；
- combination_novelty / boundary_novelty / test_migration_novelty：新增。
- similar_to：E045、DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit、
  DRAFT-snmalloc-0.7.5-ohos-mmap-va-reservation-limit
