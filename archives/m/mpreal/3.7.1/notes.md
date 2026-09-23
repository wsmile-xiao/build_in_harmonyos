# mpreal 3.7.1 适配笔记（GLM-21，2026-09-13）

## 基本信息
- 上游: https://github.com/advanpix/mpreal tag `mpfrc++-3.7.1`
- 任务号: 7365（依赖活动 activity_id=6，外部候选导入自领取）
- 分支: `feat/mpreal-3.7.1`；worktree: `~/qzy/GLM-21-mpreal-3.7.1`
- 类型: **header-only C++ 库**（单头文件 mpreal.h，MIT）
- 依赖: `mpfr/4.2.2.1`（传递引入 `gmp/6.3.0`）——R35 实证：`conan download mpfr/4.2.2.1 -r=ohpcd --only-recipe` 与 `gmp/6.3.0` 均成功（2026-09-13 设备）

## W0/W0b
- W0: 依赖已发布核验通过（见上）。
- W0b: 归档无 mpreal 历史版本（upstream/main archives/m/ 无同名归档），无历史 notes 可迁移。
- 语言预检: lang-preflight 通过（cpp，milestone=lang_checked）。

## 配方要点（header-only 房式范式）
- `package_type = "header-library"`；`package_id()` 中 `self.info.clear()`（归档既有 header-only 先例 utf8.h/doctest/7bitdi/aixlog 均此形态；v12.21 headeronly 模板的 `"library"` 未采用，以归档为准）。
- `generate()` 必须存在（CMakeToolchain(self).generate()，utf8.h 教训：漏写 → CMakePresets 缺失）。
- `build()` 仅 `apply_conandata_patches(self)`，无编译产物；不伪造编译日志。
- `package()` 只装 `mpreal.h` → include/，`copying.txt`+`README.md` → licenses/。
- conandata.yml 使用官方 GitHub archive URL + 设备实测 SHA256（`f83b4a85…e939b`）。

## 上游测试账本（R51 四维，如实申报）
1. 上游静态声明总数 N_static = **0**：证据——tag mpfrc++-3.7.1 源码树仅含 `mpreal.h`、`example/`（example.cpp + makefile 演示）、`README.md`、`changelog`、`copying.txt`；无 test/ 目录、无 ctest/check 目标、无任何测试框架（tar tzf 全量清单留档 ~/tmp/uc2/mpreal/）。
2. 官方套件实际执行 N_executed = 0（无套件可执行）。
3. 未执行/跳过 = 0。
4. 新增消费者测试 N_consumer = **1**（`test_package/test.cpp` → `test_probe`，9 个断言：set_default_prec/get_default_prec、乘法精确值、sqrt(2) 区间与平方回收、toString(20,10) 前缀、比较算符；真实链接 libmpfr+libgmp 并在真机执行）。

## 路径 B 判断
**不走 B（纯路径 A）**：本次为常规 header-only 适配，完整复用归档既有 header-only 范式（utf8.h/doctest 的 package_type/package_id/copy 三件套）与适配检查清单条目，无查重后的跨仓库新增知识；未命中知识图谱引擎（无新错误签名），无失败方案沉淀价值。判断依据：证据门槛核对（W0 依赖核验、G0-G4 全 PASS）均未产生知识库未覆盖的新问题。

## 验证记录
- conan-verify（2026-09-13，设备，CONAN_HOME=~/tmp/ch/home-glm21-mpreal）：G1/G0/G2/G3/G4/L2/L4/L5 全 PASS，`配方验证通过: mpreal 3.7.1`，可标记 published。日志：`~/tmp/uc2/mpreal/verify1.log`。
- G2 中 test_package 消费者程序编译+执行通过（test_probe 9 断言全过）。
---

**编译结束**: 2026-09-13 03:13
**最终状态**: built
