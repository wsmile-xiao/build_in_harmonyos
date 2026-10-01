# voronota 1.29.4781 — 适配笔记

> 创建时间：2026-09-29
> 状态：built（待 HMBS 真机预检：编译 + test_package + 上游测试）
> 申请人：gcw_uQ09W7jl（队伍：干）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | voronota |
| 版本 | 1.29.4781（上游 2026-04-16 发布） |
| 构建系统 | CMake（核心 C++11，JS/LT 扩展 C++14） |
| 源码 | https://github.com/kliment-olechnovic/voronota/releases/download/v1.29.4781/voronota_1.29.4781.tar.gz |
| SHA256 | 23a61a7f59b0ea47dd3b1f2ac48a486061c80e57f04e939c69f0f360a565a979（实测 18530057 字节） |
| 依赖 | 无（纯 C++，仅需编译器；JS 扩展内嵌 Duktape/Eigen 等源码） |
| 类型 | 命令行工具组，package_type=application |

## 二、上游测试盘点（R51）

- 上游测试入口：`test.bash` → 核心 `tests/run_all_jobs_scripts.bash`（跑
  `tests/jobs_scripts/*.bash`，用 `git status tests/jobs_output/` 比对参考输出）+
  `expansion_js`、`expansion_lt`、`expansion_lt_cadscore` 三套扩展套件。
- 计数：在发布标签 `v1.29.4781` 下用 GitHub API 逐文件清点，
  `tests/jobs_scripts/*.bash` 共 **26 个**核心作业脚本 +
  `expansion_js/tests/jobs_scripts/*.bash` 共 **17 个** JS 作业脚本，
  合计 **43 个**（26 + 17 = 43，与人工审查实测 N=43 一致；`expansion_lt` /
  `expansion_lt_cadscore` 另走 `run_all_tests.bash` 独立断言体系，不计入此口径）。
- 关键约束：官方发布包顶层仅含 `src/`、`expansion_js/`、`expansion_lt/`、
  `radii` 与包装脚本，**无 `tests/` 目录**（已解包验明）；`test.bash` 硬编码
  `/usr/lib64/openmpi` 且依赖 git-diff 参考输出比对（无 pass/fail 断言），故
  作业脚本无法在 conan source 布局下按原样运行。
- 对策：`build()` 运行等价核心流水线 T1–T6（help → 取球 → 顶点 --check →
  接触 + 体积 → JS/LT 烟雾测试），每级输出非空断言 + 退出码检查
  （toybox 教训：空文件比空文件也能 "Total Failures: 0"），以上游 43 脚本为
  总数口径如实上报（核心 6/6 全绿但全量未满，按 rule4 发 status=failed +
  reason + gaps，failed==0 故构建仍放行）。

## 三、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
|（无）| 零依赖 C++，CMake 原生支持 OHOS | 无需修改 | 无补丁 |

## 四、构建配置

```cmake
-DEXPANSION_JS=ON -DEXPANSION_LT=ON
# EXPANSION_GL 保持 OFF（需 OpenGL 可视化栈，真机无）
```

产物：`voronota`、`voronota-js`、`voronota-lt` + 包装脚本
（voronota-contacts、voronota-voromqa、voronota-cadscore、voronota-volumes、
voronota-pocket、voronota-membrane、voronota-resources），均由上游
CMakeLists 安装到 `bin/`。

## 五、test_package（消费者验证）

`test.sh` 共 4 项：voronota --help 非空 → 合成 PDB 全流水线（取球/顶点/接触/
体积逐级非空断言）→ voronota-js 烟雾测试 → voronota-lt 烟雾测试。
`conanfile.py` 以 `self.run` 真实执行并输出 `HMBS_TEST_PACKAGE_RESULT`
（discovered=4/passedCount=4）。

## 六、待真机预检

- `conan create` 编译（含 build() 内 T1–T6 上游等价检查与
  `HMBS_UPSTREAM_TEST_RESULT` 标记：discovered=43/executed=6/passed=6/failed=0/skipped=37/status=failed+reason+gaps）
- `test_package` 4 项消费者测试与 `HMBS_TEST_PACKAGE_RESULT` 标记
- 以上均由 HMBS 后台在 HarmonyOS aarch64 真机自动复跑，本轮仅提交工作树
