# notes.md — kicad-packages3d 10.0.3 适配笔记

## 1. 任务口径核对：本任务在平台上标注 lang=cpp，但上游没有 C/C++ 代码

平台任务（`kicad-packages3d` / `10.0.3` / `lang=cpp`）在上游对应的唯一实体是
**KiCad 官方 3D 模型库仓库** <https://gitlab.com/kicad/libraries/kicad-packages3D> 的
tag 10.0.3。该 tag 的实测内容（本地解压 `kicad-packages3D-10.0.3.tar.gz`）：

| 事实 | 证据 |
|---|---|
| 顶层 `CMakeLists.txt` 为 `project( kicad-packages3d NONE )` | tag 10.0.3 原始文件 |
| 仓库内**没有任何 C/C++ 源文件** | `tar tzf` 共 7410 个条目，`.c/.cc/.cpp/.h/.hpp` 命中 **0** |
| 唯一“构建”动作是 CMake install 3D 模型 | `install( DIRECTORY *.3dshapes DESTINATION share/kicad/3dmodels FILES_MATCHING PATTERN "*.step" PATTERN ".git" EXCLUDE )` |
| 仓库内容 | 105 个 `*.3dshapes` 目录 / 7238 个 `*.step` 模型 + 文档（README/LICENSE/CREDITS/TODO/Vrml_materials_doc）+ CMakeModules + .github |
| 发行版把它当纯数据包 | Debian `kicad-library-packages3d`（10.0.x, all）安装 `usr/share/kicad/3dmodels/*.3dshapes/*.step` |

同批次任务 `kicad-library` / `kicad-library-symbols` / `kicad-library-packages3d` /
`kicad-symbols` 同样是数据包，平台一律标 `lang=cpp`，可确认 **lang 字段是平台按套件
批量赋值的，并不表示该包含 C++ 编译单元**。

因此本 PR 的口径是：**按上游真实形态做数据/资源型包的 HarmonyOS PC 适配**，产物是
可直接被 KiCad 消费的 3D 模型资源包（与 Debian 官方包同构），而不是伪造一个 C++ 目标。

## 2. 为什么用上游 CMake 而不是自己 copy 文件

上游顶层 CMakeLists 已经把“模型目录 → share/kicad/3dmodels 安装”的完整语义写进
install() 规则：

```
project( kicad-packages3d NONE )            # 无编译器
file( GLOB SHAPE_DIRS "*.3dshapes" )
install( DIRECTORY ${SHAPE_DIRS}
    DESTINATION share/kicad/3dmodels
    COMPONENT resources
    FILES_MATCHING PATTERN "*.step"
    PATTERN ".git" EXCLUDE )
```

复用它可以保证：

1. 产物与上游/发行版**逐目录同构**（只落 `.step`，与 Debian 官方包一致）；
2. 上游 install 规则成为**真实被执行的代码路径**；
3. `project(... NONE)` 意味着不调用任何编译器 —— 交叉编译风险为零，OHOS 与原生
   构建产物完全相同。

代价：`cmake.build()` 会额外触发上游 `list_models` 自定义目标（用
`find`/`realpath --relative-to=.`/`sed`/`wc` 统计模型清单与 metrics.txt）。这些均为
标准 Unix 工具，OHOS PC 用户态环境可用；产物与架构无关。

## 3. 关于 STEP 模型格式（数据校验依据）

KiCad 3D 模型的 STEP 文件遵循 ISO-10303-21 交换结构：
```
ISO-10303-21;
HEADER;
/* ... */
DATA;
#1 = CARTESIAN_POINT('p',(0.,0.,0.));
ENDSEC;
END-ISO-10303-21;
```
消费者测试以「非空 + 以 `ISO-10303-21;` 开头 + 末尾含 `END-ISO-10303-21;`」作为
每个模型文件的数据完整性判据，可精确发现被截断/损坏的 `.step`（源码 sha256 固定，
结果确定）。

## 4. 上游测试的处置（见 test_package/MANIFEST.yml）

上游 `kicad-packages3d` 10.0.3 **仓库内没有任何测试**（逐项审计）：
- `CMakeLists.txt` 无 `enable_testing` / `add_test` / `include(CTest)` / `BUILD_TESTING`；
- 仓库内 0 个 C/C++ 源文件、0 个 Python/Shell 脚本；
- 无 `.gitlab-ci.yml` 或任何 CI 测试配置（唯一 `.yml` 为 `.github/lockdown.yml`，
  GitHub issue 锁定机器人，非测试）。

因此按仓库规范 `upstream_tests_exist: false` + 非空 `upstream_test_audit` +
`upstream_test_total: 0`（status `no_tests`）。适配后由
`test_package/test_kicad_packages3d.py` 从消费者视角真实消费被测包（21 条断言），
随每次 `conan create` 在 CI 中回归。

## 5. 踩坑记录

1. **`package_type` 不能用 `"application"`** —— 同 kicad-symbols：CI 门禁 L0k（R38）
   以 `package_type == "application"` 作为“本包含命令行工具”的判据，会强制要求软件级
   `commands.json`。本包无 bin/，用 `package_type = "unknown"` + `cpp_info.resdirs = ["share"]`。

2. **只安装 `.step`，不安装 `.wrl`** —— 上游 install 规则 `FILES_MATCHING PATTERN "*.step"`
   只装 STEP。tag 10.0.3 仓库内本身也**只有 STEP 文件（0 个 .wrl）**。这与 Debian 官方
   包一致（KiCad 以 STEP 为首要 3D 数据源）。消费者测试按 STEP 计 7238 个。

3. **`sharedir` 布局是 `share/kicad/3dmodels`** —— 不是 `share/kicad/packages3d`。
   上游用变量 `KICAD_PACKAGES_3D=${KICAD_DATA}/3dmodels`（`KICAD_DATA=share/kicad`）。
   消费者测试、manifest、notes 均按该路径。

4. **tag 10.0.3 的 tarball 较大（632 MB 压缩）** —— 这是 KiCad 官方 3D 模型库的固有
   体量（7238 个 STEP 模型）；conandata 固定官方源 sha256，真机在 Conan 缓存中只下载
   一次。

5. **`HMBS_TEST_PACKAGE_RESULT` 标记必须是单行、独立 JSON 对象** —— 早期版本在脚本
   末尾打印的是 `{"HMBS_TEST_PACKAGE_RESULT": {...}, "checks": {...}}` 这种**复合对象**，
   门禁按 `HMBS_TEST_PACKAGE_RESULT={...}` 解析 `=` 后到行尾的内容作为独立 JSON，
   遇到行尾多余的 `, "checks": ...}` 会解析失败 → 判为"缺少 test_package 真实用例计数
   和机器测试证据"（incomplete）。修正为打印形如
   `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"...","discovered":21,"passedCount":21}`
   的**独立单行**标记（与 aribb24/alass 等已过门禁的先例一致）。

6. **no_tests 上游必须复发 `HMBS_UPSTREAM_TEST_RESULT` 标记（rule4 硬门禁）** ——
   test_package 的 `HMBS_TEST_PACKAGE_RESULT` 单通过是不够的。门禁同时要求上游运行结果
   标记：对确认无测试的上游，必须在真实运行 test_package（输出
   `HMBS_TEST_PACKAGE_RESULT`）**之后**，用 `json.dumps` 复发一行
   `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"",
   "discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"…MANIFEST.yml
   审计结论…"}`（status=no_tests、各计数为 0、reason 引用 MANIFEST.yml 的
   upstream_test_audit 审计）。缺此标记 rule4 判「缺少上游运行结果」
   （discovered/executed/passed 全 0）→ incomplete。与 udns/0.6 同根因。

## 7. 一致性核对（数据来源）

- 归档条目数 7410、`.3dshapes` 目录数 **105**、`.step` 文件数 **7238** —— 均为
  `tar tzf` 直接统计；
- 单个 STEP 实测：`R_01005_0402Metric.step` 40419 字节，`ISO-10303-21;` 头 /
  `END-ISO-10303-21;` 尾闭合；
- 各抽样目录 STEP 数实测：Resistor_SMD 40、Package_DIP 204、Package_TO_SOT_THT 93、
  Capacitor_SMD 91、Diode_SMD 38 —— 与测试 KNOWN_MODELS 阈值一致；
- 已知模型文件名实测：`R_01005_0402Metric` / `DIP-10_W7.62mm` /
  `Analog_TO-46-4_ThermalShield` / `CP_Elec_10x10` / `D_0603_1608Metric`。
