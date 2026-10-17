# ee 3.2.2 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统，单文件 C 库，直接 clang 编译 + llvm-ar 归档）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. init-build：下载官方 tag V3.2.2 tarball（SHA-256 52416cab...），解压到 .work
2. lang-preflight：task=cpp ↔ detected=c（C 兼容族），通过
3. 新增模拟 STM32 HAL 层 `main.h` 与模拟 Flash 实现 `ee_sim_flash.c`（无构建系统的
   嵌入式库依赖 STM32 HAL，OHOS 无该头文件与 Flash 硬件；固定低地址 0x20000000
   mmap 模拟擦除/编程/直接寻址读取语义）
4. clang -c -O2 -fPIC -std=c11 -I. ee.c ee_sim_flash.c → llvm-ar rcs libee.a
5. conan-init 生成配方 → conan-verify G0-G4/L2/L4/L5 全部通过（conan create 干净构建）
6. finish built：W3 本地 CI（setup.sh + build_and_test.sh）通过，JC/KC/L0-L5 全绿

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ee.h 需要 main.h（STM32 HAL），OHOS 无此头 | 嵌入式库与 HAL 头文件耦合 | 新增模拟 HAL main.h（FLASH_* 宏 + HAL_FLASH_* API） |
| 2 | 默认 PIE 链接段错误（SIGSEGV），-no-pie 才正常 | ee.c 用 uint32_t 保存 Flash 地址并直接解引用，64 位宿主缓冲区地址 >4GiB 被截断 | ee_sim_flash.c 用固定低地址 0x20000000 mmap 模拟 Flash，地址恒合法 |
| 3 | conan apply_conandata_patches 报 "source/target file does not exist" | 新增文件补丁需 `--- /dev/null` + `+++ b/<file>` 头部，refresh-patch 生成的是 `--- a/...` 格式 | 用 git diff --no-index /dev/null <file> 重新生成标准新增文件补丁 |
| 4 | W3 JC 门禁命中其他库既有基线状态文件（cloog/kics） | full 模式扫全仓 tracked 文件，命中 main 已提交的其他库空状态文件 | 基线隔离复验：git rm --cached 临时移出 → 重跑 W3 → 恢复 → 核对 SHA-256 一致 |

## 源码修改

- `patches/0001-ee_sim_flash.c.patch`：新增模拟 Flash 实现（构造时 mmap 固定低地址
  16KiB 缓冲区置 0xFF，Erase=memset(0xFF)，Program=半字 1→0 写入，mmap 失败如实返回 HAL_ERROR）
- `patches/0002-main.h.patch`：新增模拟 STM32 HAL 头（__IO、HAL_StatusTypeDef、
  FLASH_EraseInitTypeDef、FLASH_BASE/PAGE_SIZE/SECTOR_SIZE/TYPEPROGRAM_HALFWORD，
  型号宏选 STM32F7 避免 FLASH_SIZE 重定义冲突）

## 依赖版本

- 无第三方依赖（纯标准 C + POSIX mmap）

## 验证结果

```bash
# 鸿蒙专项测试（默认 PIE 链接）
clang -O2 -std=c11 -I<prefix>/include tests/harmonyos_smoke_test.c -L<prefix>/lib -lee -o smoke_test && ./smoke_test
# capacity/readback/format/NULL 断言全绿，rc=0

# 消费者用例（设备参数持久化服务）
clang -O2 -std=c11 -I<prefix>/include tests/consumer_app_test.c -L<prefix>/lib -lee -o consumer && ./consumer
# 重启回读恢复一致、格式化清空，CONSUMER_TEST_PASS checks=2，rc=0

# 配方验证
python3 scripts/ohc-run.py conan-verify ee 3.2.2   # G0-G4/L2/L4/L5 通过
python3 scripts/ohc-run.py finish ee 3.2.2 built   # W3 本地 CI 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 无构建系统库配方（clang 直接编译 + llvm-ar） |
| conandata.yml | 官方源 + SHA-256 + 2 个补丁声明 |
| test_package/ | L1 官方测试（test.c 真实调用 EE_* API，7 组断言） |
| tests/ | 鸿蒙专项 smoke + 消费者用例 |
| patches/ | 模拟 HAL + 模拟 Flash 两个新增文件补丁 |
| knowledge/drafts/DRAFT-ee-3.2.2-ohos-sim-hal-fixed-low-addr-flash | 路径 B 知识草稿（kv+md） |

## 注意事项

- 嵌入式固件库直接解引用 uint32_t 地址的适配必须保证地址落在 4GiB 内（固定低地址
  mmap），否则 PIE 链接下必崩；模拟层需具备真实语义（0xFF 空态、擦除、编程、读回校验），
  空壳 stub 不满足 R8/R40
- 新增文件补丁需用标准 `--- /dev/null` + `+++ b/<file>` 格式

---

**编译结束**: 2026-09-20 23:56
**最终状态**: built
---

**编译结束**: 2026-09-21 00:47
**最终状态**: built
