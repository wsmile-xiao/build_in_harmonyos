# DRAFT: 无构建系统嵌入式 C 库的 Conan 2 直编配方 + 空占位宏补值 + RAM 模拟 flash 测试

> 知识草稿（与 `DRAFT-easyflash-4.1.0-no-build-direct-compile.kv` 配对）
> 来源：easyflash 4.1.0 第一轮适配（executor pc2-41，task easyflash-4.1.0-r01-pc2-41-20260918T190856Z）

## 问题

适配 easyflash 4.1.0（armink/EasyFlash，嵌入式 flash 键值库）时遇到四类可跨库复用问题：

1. **上游无任何构建系统**：全树清点确认无 configure/Makefile/CMakeLists/meson/构建脚本。
   conan-init 默认 autotools 模板不可用，需在 `build()` 内逐 TU 直编。
2. **Conan 2 配方三处 API 陷阱**：
   - `self.copy` 属性不存在（须 `from conan.tools.files import copy` 后 `copy(self, ...)`）；
   - `tools.build:archiver` 不是合法 conf（读 `AR` 环境变量兜底 `llvm-ar`）；
   - `self.source_folder` 在 `package()` 阶段不可用 → 必须在 `build()` 内把头文件
     staging 到 `build_folder`，`package()` 只从 `self.build_folder` 复制。
3. **空占位必需配置宏**：`ef_cfg.h` 把 `EF_ENV_VER_NUM / EF_ERASE_MIN_SIZE /
   EF_WRITE_GRAN / EF_START_ADDR / ENV_AREA_SIZE` 留作无值占位（`@note you must
   define it`），消费者直接 include 即编译失败，必须补丁补值。
4. **无 MCU flash 的测试移植**：`ef_port.c`（read/erase/write/print）由使用者实现，
   OHOS PC 无 MCU flash，需 RAM 模拟 NOR 语义（erase 置 0xFF、write 仅 1→0）的
   移植层才能端到端运行 ENV 键值 API。

## 根因

- 嵌入式库面向 MCU 集成场景设计，不带通用构建系统与默认配置值；
- Conan 2 的 `copy`/archiver/source_folder 语义与 Conan 1 及直觉不同；
- 平台移植层与配置宏天然由使用者提供，测试必须自备等价物。

## 方案

- `build()`：`${CC:-clang} -fPIC -O2 -I<src>/easyflash/inc -c <src>/easyflash/src/*.c`
  逐个生成 .o → `${AR:-llvm-ar} rcs libeasyflash.a *.o` → `mkdir include && cp 头文件`
  （staging 到 build_folder）；
- `package()`：仅从 `self.build_folder` 用 `copy(self, "include/*.h", dst="include",
  src=self.build_folder)` 与 `copy(self, "libeasyflash.a", dst="lib", ...)`；
- 补丁（patches/0001-easyflash-inc-ef_cfg.h.patch）：给空占位宏补 RAM 模拟布局值
  （EF_ERASE_MIN_SIZE=4096、EF_WRITE_GRAN=8、EF_START_ADDR=0、ENV_AREA_SIZE=8192、
  EF_ENV_VER_NUM=0）；
- test_package：`ef_port_ram.c` RAM 模拟 flash（首次 init 置 0xFF、此后保留内容模拟
  掉电保留）+ 消费者测试（test.c）与鸿蒙专项测试（ohos_env_test.c，二进制 blob 往返
  含内嵌 NUL、re-init 持久化、默认环境恢复）。

## 验证

- `conan create archives/e/easyflash/4.1.0 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
  → exit 0；test_package 两个可执行用例全部 PASS（消费者 10/10、鸿蒙专项 13/13）；
- `finish easyflash 4.1.0 published` → status=published，W3 本地 CI 模拟通过
  （reports/w3-local-ci.log）。

## 适用边界

- 适用：无构建系统的嵌入式 C 库（flash/KV/键值存储类）；带空占位必需宏的头文件；
  依赖 package() 复制产物的直编配方。
- 不适用/反例：上游确有 CMake/Makefile 的库（应走标准构建）；header-only 库
  （见既有 E321/E322/E257）；stb 风格单头实现库（见既有 DRAFT-enet 草稿）。

## 七轴查重（对既有知识库）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无任何既有条目覆盖"无构建系统库直编 + 空占位宏补值 + RAM flash 移植层"组合 |
| causal_duplicate | false | E257（header-only no-op build）根因是 G1 缺 build()，与本例"确需直编"不同因 |
| trigger_overlap | partial | E307（test_package 直编）仅在"直编编译器"触发面上部分重叠，其场景是 header-only 且 compile-only |
| solution_overlap | partial | E311（source-folder isolation）在"source_folder 语义"上部分重叠，但未覆盖 package() 阶段不可用与 staging 方案 |
| combination_novelty | true | 直编 + staging 头文件 + 空占位宏补值 + RAM 模拟 flash 四者组合无既有条目 |
| boundary_novelty | true | "无构建系统、非 header-only、嵌入式存储库"边界未被既有条目覆盖（E257 是 header-only） |
| test_migration_novelty | true | RAM 模拟 NOR flash 移植层驱动真实公共 API 端到端测试（含二进制 blob/掉电持久化）为新增测试迁移模式 |

## 路径判定

**path B（知识库扩展，new_draft）**：候选已验证（conan create + 双测试全过）、可跨库复用
（任何无构建系统嵌入式库/空占位宏头文件），查重为未命中或部分覆盖且存在新增差异。
已建同 stem 草稿对：
- `knowledge/drafts/DRAFT-easyflash-4.1.0-no-build-direct-compile.kv`
- `knowledge/drafts/DRAFT-easyflash-4.1.0-no-build-direct-compile.md`
