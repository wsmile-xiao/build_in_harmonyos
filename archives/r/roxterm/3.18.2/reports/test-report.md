# roxterm 3.18.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 真机（profile ohos-aarch64，clang OHOS SDK native llvm）
- Conan 2.29.1（OHOS 适配版）
- Source: https://github.com/realh/roxterm/archive/refs/tags/3.18.2.tar.gz
  sha256 d20a19abe03798bfc6c9404eb7ce4fbecabf2e1ab527b587aab76d06635a92e7

## Verification

- `ohc-run.py conan-verify roxterm 3.18.2`: exit 0
  - G0 PASS（知识图谱预查询，E092 已在配方处理）
  - G1 PASS（配方结构/完整性）
  - G2 PASS（干净 `conan create`，依赖全部取自 ohpcd 制品仓已发布 binary）
  - G3 PASS（R26 系统同名库隔离）
  - G4 PASS（产物完整性）
  - L2/L4/L5 PASS

## Upstream tests (R51 三步法)

- 清点：上游 `src/` 无 enable_testing/add_test、无 tests 目录、无 CTest/`make check` 目标 —— **N=0**，
  无上游测试可执行（test_package/MANIFEST.yml 已记录证据）。
- 替代验证：test_package 三层探针（klavaro 模式）
  1. ELF magic + AArch64：roxterm、roxterm-config 均 PASS
  2. DT_NEEDED 闭包 32 库完整（vte/gtk3/gdk/glib/pango/cairo 等全部可解析）PASS
  3. 启动探测 `roxterm --usage`：动态加载器完整解析闭包，headless 下 GTK init 报
     "Cannot open display"（预期 PASS，证明库加载成功）；loader error 记 FAIL —— 实测 PASS
- 通过率：**100%（N=0 上游测试 + 探针 3/3 通过）**

## Package smoke (R34)

- `bin/roxterm --usage`、`bin/roxterm-config` AArch64 动态 ELF，codesign 自签后真机可执行
- packaging/roxterm-3.18.2-ohos-aarch64.tar.gz：bin/ + share/（icons、Config、locale、desktop、metainfo）
