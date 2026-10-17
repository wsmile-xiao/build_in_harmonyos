# gplotpp 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang/clang++ (OHOS SDK 15)
- 状态: built

## 编译步骤

```bash
# 源码: 官方 GitHub tag v1.1.0 归档
#   https://github.com/ziotom78/gplotpp/archive/refs/tags/v1.1.0.tar.gz
#   sha256: 5d6d411abfd6283ace3aa9f41a34d2cdccad5ceed21d486d2a64318a974d9661
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    -DGPLOTPP_ENABLE_TESTS=ON -DGPLOTPP_BUILD_EXAMPLES=OFF
cmake --build build --target run_tests -j4
# 上游测试: ./tests/run_tests  (doctest, 2 TEST_CASE / 5 断言)
#   [doctest] test cases: 2 | 2 passed | 0 failed | 0 skipped
#   [doctest] assertions: 5 | 5 passed | 0 failed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | 探测逻辑对无 configure 的 CMake INTERFACE 库误判 | conan-init 后手工改写为 CMake header-library 配方（参照 gcem） |
| 2 | 上游测试需要真实 gnuplot 可执行文件 | gplotpp 通过 popen 驱动 gnuplot | ohpcd 制品仓已有 gnuplot/6.0.3 OHOS 包，配方 build() 与 test_package 从 PATH/conan2 缓存定位并注入 |
| 3 | gnuplot gif/svg 终端能力受限 | OHOS gnuplot 构建缺 gd/cairo 终端 | 上游 animation 用例无断言仅编译运行（如实记录）；complex 用例 SVG 标签断言全部通过；消费者/鸿蒙专项测试改用 dumb 终端做真实渲染断言 |

## 源码修改

无（header-only 库，无需补丁）。

## 依赖版本

- gnuplot 6.0.3（运行时工具，来自 ohpcd 制品仓；非库构建依赖）

## 验证结果

```bash
# 上游测试（真实 gnuplot 6.0.3 注入）
[doctest] test cases: 2 | 2 passed | 0 failed | 0 skipped
[doctest] assertions: 5 | 5 passed | 0 failed
# 消费者验证（test_package）：dumb 终端渲染 + 标签核验
# test_ohos（4 项：ELF/musl/无宿主路径/真实制图）全通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-library 配方（含上游测试运行） |
| conandata.yml | 官方 tag 源码 + SHA-256 |
| test_package/ | 消费者用例（真实 Gnuplot API + 输出核验） |
| test_ohos/ | 鸿蒙 PC 专项验证（4 项检查） |

## 注意事项

- gplotpp 是 header-only INTERFACE 库，仅安装 gplot++.h 与 CMake config。
- 消费者运行时需要 gnuplot 可执行文件（如 ohpcd 制品仓 gnuplot/6.0.3）。

## 知识候选台账与查重

### 候选 1：header-only 库上游测试运行时工具注入（gnuplot）— R02 修订
- 真实错误（R01→R02）：`sh: gnuplot: inaccessible or not found` → `CHECK(fin != nullptr)` 失败 SIGABRT（本地/CI 均复现）
- R02 新增差异（远端 CI 复验发现）：仅本地 conan2 缓存注入在远端 CI 干净环境不成立 → `GPLOTPP_GNUPLOT_BIN=NOT_FOUND` → L1_RESULT=fail；正确方案是配方 `build_requirements()` 声明 `tool_requires("gnuplot/6.0.3")`（test_package 同样声明），`_find_gnuplot_bin()` 优先 `self.dependencies.build["gnuplot"].package_folder`，缓存 glob 仅兜底；找不到 gnuplot 时 raise RuntimeError 拒绝运行上游套件（禁止静默跳过）
- 根因：上游测试/消费者经 popen 驱动真实 gnuplot；OHOS 无系统 gnuplot；conan2 缓存目录名被哈希截断（`gnupla03c6b9f7091e`）glob `gnuplot*` 不中；HMDFS 忽略 chmod `os.access(X_OK)` 恒 False；Conan2 `self.run(env=dict)` 断言报错；CTest 不继承注入 PATH
- 修复：tool_requires 声明 + 依赖目录优先定位 + 命令内嵌 `export PATH` + 直跑二进制避开 CTest + 断言改用 SVG 终端（OHOS gnuplot 缺 gd）
- 验证：R02 conan create 复验 GPLOTPP_GNUPLOT_BIN 检出真实二进制，上游 2/2、断言 5/5；消费者退出码 0；test_ohos 4/4（T3 已修）
- 适用范围：header-only/无构建库需要外部运行时工具（gnuplot 类）且要求远端 CI 干净环境可用的注入
- 四范围查重：正式知识未命中（E540 runner PATH、E307 header-only 直编、E298 conanrun、E046 chmod、E321 header-only 配方——均部分相关不同题）；图谱未命中；草稿未命中；doc 未命中
- 判定：**new_draft**（DRAFT-gplotpp-1.1.0-runtime-tool-injection.kv/.md 配对，R02 已修订），走路径 B

### 候选 2：新库零提交时 W3 junk_check 回退 full 模式命中其他库基线噪声
- 真实错误：`检查模式: full (88718 个文件)` → `JC5: archives 下未登记的隐藏文件`（cloog/kics 的 .build-closed/.staging-verified）
- 根因：junk_check 模式链 pr.diff > incremental > full；零提交分支三点 diff 为空回退 full 整仓索引扫描
- 修复：先 commit 本库工作使 diff 非空 → incremental 只扫本库（等价 DRAFT-boost-te 方案）
- 验证：commit 后 W3 `incremental` 模式通过 100%
- 适用范围：共享 build_in_harmonyos 仓库新库分支
- 四范围查重：草稿全覆盖（DRAFT-boost-te、DRAFT-dr_mp3、DRAFT-fastnoiselite、DRAFT-libfort、DRAFT-libpopcnt、DRAFT-micro-ecc 等）
- 判定：**reuse_existing**（复用既有知识，无新增差异）

### 候选 3：Conan2 `self.run(env=...)` 只收列表/dict 断言
- 真实错误：`AssertionError: env argument to ConanFile.run() should be a list`
- 根因：Conan 2 env 参数只接受 generator 名或 VAR=VALUE 字符串列表
- 修复：`env=["VAR=VALUE", ...]` 或命令内嵌 export
- 四范围查重：正式知识 E501、草稿 DRAFT-8945-botan3 已覆盖
- 判定：**reuse_existing**

### 候选 4：HMDFS `os.access(X_OK)` 恒 False（工具探测误判）
- 真实错误：`shutil.which` 与 `os.access` 均找不到实际存在的 gnuplot
- 根因：HMDFS 忽略 chmod（E046/R49），权限固定 660
- 修复：改用 `os.path.isfile` 过滤
- 四范围查重：正式知识 E046 已覆盖根因，本候选为其在运行时工具定位场景的延伸（已并入候选 1 的 new_draft）
- 判定：**reuse_existing** + 并入候选 1

### 候选 5（R02 新增）：test_ohos T3 伪通过（readelf -d 失败被当作 PASS）
- 真实错误：`readelf_d = r.stdout if r.returncode == 0 else b""` → readelf -d 非 0 时输出为空、has_rpath 恒 False → T3 伪报 PASS
- 根因：工具失败分支被静默当作"无 RPATH/RUNPATH"结论
- 修复：readelf -d 非 0 即打印 stderr 并 return 1（与 T1/T2 一致），仅在成功解析时判定
- 验证：R02 重跑 test_ohos 4/4 通过（T3 逻辑已修复）
- 适用范围：所有用 readelf/strings 做机器检查的 test_ohos 脚本
- 四范围查重：未命中既有条目（属通用检查脚本健壮性，简单修复）
- 判定：并入候选 1 草稿的验证段说明；无独立新增知识价值（通用编码健壮性）

### 路径决定
- 候选 1 已验证、可跨库复用、查重部分覆盖且有新增差异（R02 tool_requires 修订）→ **路径 B（new_draft）**，草稿与归档同 PR
- 候选 2/3/4 完整重复或已有覆盖 → 复用既有知识（对应路径 A 行为）
- 候选 5 为通用健壮性修复，无独立知识价值 → 不单独立项
- 结论：`new_draft` + `reuse_existing`（混合），主路径为 B
---

**编译结束**: 2026-09-26 01:07
**最终状态**: built
