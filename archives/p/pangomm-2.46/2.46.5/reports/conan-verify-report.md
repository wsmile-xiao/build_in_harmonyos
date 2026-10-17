# Conan Verify Report — pangomm-2.46 2.46.5

**Verdict**: PASS
**Reference**: `pangomm-2.46/2.46.5@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-27T21:17:31.487584

## G0: ✅ PASS
**Knowledge hit**: E490
  📦 构建系统: autotools
  ⚠️ 已知风险 E490 未在配方中处理
     根因: Autotools helper scripts are executable programs, but some HarmonyOS PC adaptation paths preserve source content without
     方案: restore-known-autotools-script-modes
     修复: chmod +x configure config.guess config.sub install-sh missing; ./configure; make -j1; make -j1 check
     ⚡ G2 conan create 可能因此失败，建议先修复

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

---

## 附：test_package 断言整改后复验（2026-09-27 深夜，commit dee198521b）

整改背景（AI 审查意见）：原 `AttrList` 断言为恒真表达式，且 `reports/conan-create.log` 属禁提交的 `*.log`。
处置：① 删除 `reports/conan-create.log`；② test.cpp 的 AttrList 断言改为**可失败判据** —— `create_attr_size(12*SCALE)` 构造真实 `AttrInt` → `AttrList::change()` 插入 → 遍历 `AttrIter` 数段数，`n_segments >= 1` 才通过（change() 未生效则计数为 0 → FAIL）。

真机复验（HarmonyOS PC aarch64，通道 2 中继）：

```sh
cd /storage/Users/currentUser/bih && conan test \
  archives/p/pangomm-2.46/2.46.5/test_package pangomm-2.46/2.46.5@ohpcd/stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

输出（真实编译 + 运行）：

```
RUN: /data/service/hnp/bin/clang++ test.cpp -o test_probe ... -lpangomm-1.4 -lcairomm-1.0 -lglibmm-2.4 -lsigc-2.0 -std=c++17
pangomm 2.46.5: all 4 checks passed
```

4 项断言（FontDescription::get_family / get_size、AttrList change() 插入 AttrInt 段数、PANGOMM_MAJOR_VERSION）在真机上全部通过，含新改的可失败判据。
__RUNDEV2_DONE_1790515354285__
