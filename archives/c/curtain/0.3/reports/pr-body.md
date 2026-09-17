## 三方库信息

- **三方库名称**：curtain
- **上游版本**：0.3
- **上游仓库地址**：https://code.google.com/archive/p/ardesia/ （官方历史归档：https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/ardesia/curtain-0.3.tar.gz，SHA256 `a361bf9edb85c35b9080458b9d68abae409825837f8a24207a9e62ea43950adb`）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新，见下方"路径 B 知识贡献说明"）
- **使用知识库**：E527/E463/E471（OHOS GTK 仅 Broadway 的构建级背景）、E540（CI runner 参考）；本 PR 携带 3 条知识草稿（E429-draft-9C4A 补丁格式 + 2 条路径 B 知识，见下节）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | configure.ac 无 AM_TESTS；各 Makefile.am 无 TESTS/check_PROGRAMS；无 test 目录 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **0** | 上游确无自动化测试套件（清点证据见 notes.md） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 28 | +28 | `bin/curtain_check`：四边揭开/回盖几何、最小尺寸钳制、关闭热区、缩放正确性；真机执行 28/28 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 16 | 新增 | `test_package`：AArch64 ELF、DT_SONAME、`libace_napi.z.so` NEEDED、适配树、rawfile 幕布图、许可证；16/16 |
| **合计** | **44** | **+44** | 通过率 100% |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（下方逐条说明）

说明：上游源码零修改；34 个补丁全部为新增文件（ArkUI 宿主工程、C 核心、NAPI、回归检查）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：C 核心几何状态机（逐分支移植上游 `src/callbacks.c`）与缩放语义
  （对应 `src/utils.c::scale_surface`），共 28 项断言；消费者侧 `test_package` 16 项
  包结构/链接/产物断言。
- **补全原因**：上游无任何自动化测试套件（N=0，证据见 `notes.md` 与 `test_package/MANIFEST.yml`）。
- **新增测试文件清单**：
  1. `harmony/project/entry/src/main/cpp/check/curtain_check.c` — 28 项无头回归断言（几何 + 缩放）
  2. `harmony/project/entry/src/main/cpp/CMakeLists.txt` — 构建 `curtain_check` 并注册 CTest
  3. `test_package/test.sh` — 运行包内 `curtain_check` 并校验包结构（16 项断言）
  4. `test_package/conanfile.py`、`test_package/MANIFEST.yml` — 消费者测试入口与申报

## 验证结果

- 编译状态：**通过**（`conan create` 干净构建，34 个补丁全部应用；CMake + OHOS SDK clang 15.0.4）
- 上游测试用例通过率：**0/0**（上游无测试，已说明）；新增适配回归 28/28（100%）
- 新增测试用例通过率：**44/44（100%）**（28 回归 + 16 消费者）
- 配方验证：`conan-verify` G0-G4 全部 PASS；本地 CI 门禁 L0/L1/L1e/L2/L5 PASS
  （L4 的 `targets` 误匹配 `gets` 为已知误报）
- 真机验证（HarmonyOS 6.1.0.117，3120x2080）：全屏遮罩、拖拽揭开（横向/纵向）、
  点击穿透、拖拽回盖、右上角 X 关闭、重启——全部 PASS，证据见 `reports/test-report.md`
  第 4/6 节（截图 + hilog 摘录）。

## 路径 B 知识贡献说明

本 PR 按**路径 A+B** 申报：归档适配与知识草稿在**同一 PR 原子交付**（先例：#9734 cdo、#9735 cln、#9665 quirc、#9670 ncmpc），kv+md 成对随分支 `feat/curtain-0.3` 提交，不另开知识 PR。

知识库扩展 Issue：[#3032](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3032)（与本 PR 双向关联）

Closes #3032

### 本 PR 携带的知识草稿

| # | 草稿（kv + md 成对） | 知识主题 | 触发实例 |
|---|---------------------|---------|---------|
| 1 | `knowledge/drafts/E429-draft-9C4B.kv/.md` | 无原生显示后端的桌面 GUI 应用在 OHOS PC 的运行时适配模式 | curtain 0.3：GTK broadway-only 直启失败 → ArkUI 原生宿主 + C 行为核心移植 |
| 2 | `knowledge/drafts/E429-draft-9C4C.kv/.md` | ArkTS/NAPI 像素缓冲集成契约（external ArrayBuffer 不可用；异步 release 时机） | curtain 0.3：`colors mismatch` 1 次 + 进程崩溃（cppcrash）3 次 |
| 3 | `knowledge/drafts/E429-draft-9C4A.kv/.md`（原 A 阶段已随本 PR 提交） | 新增文件补丁必须 `--- /dev/null`；refresh-patch dry-run 污染 `.orig` | 34 个新增文件补丁实测 |

### 草稿 1：无原生显示后端的桌面 GUI 应用运行时适配模式

- **主题**：当上游 UI 工具包在 OHOS 只提供 Broadway（浏览器输出）后端时，如何以"ArkUI 原生宿主 +
  行为核心 C 移植 + 窗口矩形=幕布/组件矩形"重建桌面窗口行为（全屏覆盖、拖拽揭开、点击穿透），
  并给出可复制的验证组合拳（无头回归 + test_package + 真机 uinput/截图逐行为取证）。
- **触发实例**：curtain 0.3（GTK3 遮罩工具）；`gtk_init` 失败（`Gtk-WARNING: cannot open display`）；
  Broadway 渲染进浏览器不能覆盖原生桌面。
- **查重结论（`draft-review` 实测）**：最相似 E527 score=0.41、E471 score=0.40、E530 score=0.26，
  预审建议 `review-similar → E527`（灰区，需人工判断）。人工比对：E527（Broadway 后端下的
  meson 工具包装）、E471（无显示服务→测试分类）、E463（HMDFS 资源编译）三者的结论面均为
  **GTK 构建/测试级**（"怎么把 GTK 搭起来、怎么分类测试"）；**无一条覆盖应用级运行时**问题
  （"显示后端缺失后，应用行为如何换宿主重建"）。新增价值即宿主替换模式 + 窗口几何等价实现
  遮盖/穿透 + 验证方法。
- **验证证据**：真机 6 项行为全部 PASS（截图 + hilog，见 `reports/test-report.md` 第 4/6 节）；
  无头回归 28/28；`conan-verify` G0-G4 PASS。

### 草稿 2：ArkTS/NAPI 像素缓冲集成契约

- **主题**：① `image.createPixelMap` **不接受** NAPI external ArrayBuffer（实测
  `PixelMapNapi: colors mismatch`，或进程崩溃），NAPI 必须返回拷贝的 ArrayBuffer
  （`napi_create_arraybuffer` + `memcpy`）；② 异步图像对象（ImageSource/PixelMap）必须在
  **全部 `await` 完成后统一 `release()`**，否则 Promise 续体会触碰已释放对象，产生
  SIGSEGV（use-after-free）。
- **触发实例**：curtain 0.3 真机适配；`colors mismatch` 1 次（hilog 14:12:39）；cppcrash 3 次
  （14:14:45 / 14:18:59 / 14:20:18），崩溃栈特征
  `#01 at initAsync entry (Curtain.ets)` + 提交栈 `PixelMapNapi::ReadPixelsToBuffer`。
- **查重结论（`draft-review` 实测）**：全库检索 `PixelMap` 0 命中、`napi_` 无相关条目；
  TOP1 相似度 0.03，预审建议 **create**（疑似新知）。与 E474（ArkUI 消费者验证契约）、
  E462（SIGSEGV 调试）、E321（图形栈 API 面）主题均不同：本条首次沉淀
  "NAPI↔ArkTS 像素缓冲"的两类运行时契约与验收口径。
- **验证证据**：修复后 `pixelMap=true`、无 `colors mismatch`、faultlog 无新增 cppcrash、
  截图真实画面；修复包含在 `d7103a553`（拷贝缓冲 + 延后 release）与 `e36b48dfa`（NAPI 加固）。

### 草稿 3：新增文件补丁格式与 `.orig` 污染（原 A 阶段已交付）

- **主题**：`conan apply_conandata_patches`（patch_ng，strip=0）要求新增文件补丁头为
  `--- /dev/null` / `+++ b/<path>`；`refresh-patch` 的 GNU patch dry-run 会在 `.orig` 创建
  空文件，二次 refresh 把其误判为修改文件，导致 `conan create` 失败。
- **触发实例**：curtain 0.3 的 34 个新增文件补丁（宿主工程 + C 核心 + NAPI）。
- **查重结论**：与 E515（`a/ b/` 头需 strip:1）、E254（toybox patch dry-run 污染，建议改用
  export_sources）、E526（校验语义须与 patch_ng 一致）最相似；本条增量为**新增文件场景的
  `/dev/null` 头规则 + 本仓库 refresh-patch 的清理/重生成流程 + `patch_ng` strip=0 探针验证法**。
- **验证证据**：34 个新增补丁在 `conan create` 全量应用成功；`patch_ng` strip=0 试应用探针。

## 补充说明

- **升级说明**：本 PR 原按路径 A（【积分赛】）提交，现按知识库扩展先例（#9734/#9735——
  同一 PR 升格、知识草稿原子交付、标题前缀改【知识库扩展】）升级为**路径 A+B**，
  并新开知识库扩展 Issue [#3032](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3032)
  双向关联；归档产物、测试与真机验证结果不变，无任何回退。
- **适配方式**：OHOS 已发布的 GTK 仅 Broadway 后端（浏览器内显示，不能覆盖原生桌面），
  因此保留上游源码、新增 ArkUI 原生宿主（`harmony/project`）承载全屏窗口与触摸，
  并把上游 `callbacks.c` 的拖拽几何与 `utils.c` 的缩放语义移植到 C 核心（`curtain_core.c`）；
  窗口矩形即幕布矩形，拖拽释放后调整窗口 move/resize，窗口之外即桌面，
  天然实现揭开区域可见与点击穿透（等价上游 `gtk_widget_input_shape_combine_region`）。
- **已知限制**：
  1. `setWindowTopmost` 需系统权限 `ohos.permission.WINDOW_TOPMOST`，实测返回 201；
     被点击拉起的其他窗口可盖住幕布，需重新启动应用置前（核心行为不依赖该权限）。
  2. 自由窗口状态下幕布最顶部边缘可能被系统窗口热区/悬浮标题栏占用；
     最大化/全屏状态下 X 点击实测正常。系统 Dock 始终绘制在幕布之上。
  3. 随包不发布 GTK/Broadway 版二进制：Broadway 不能覆盖桌面，不能作为适配完成证据；
     上游 GTK 源码随归档完整保留。
- **依赖**：无 Conan 运行时/构建依赖；构建工具来自 OHOS SDK（clang 15.0.4、CMake）。
- **知识草稿**：`E429-draft-9C4A`（补丁格式，原 A 阶段）；`E429-draft-9C4B`（运行时适配模式）；
  `E429-draft-9C4C`（ArkTS/NAPI 像素缓冲契约）。
- **验证命令**：
  ```bash
  # 干净构建 + G0-G4 + CTest + test_package
  conan create archives/c/curtain/0.3 -pr:h=<profile> -pr:b=<profile> --build=missing
  # 预期：G0-G4 PASS；curtain_check 28/28；test_package 16/16

  # 本地 CI 门禁模拟（与平台 CI 同源脚本，增量模式）
  CONAN_PROFILE=<profile> CI_PACKAGES=archives/c/curtain/0.3 \
    zsh ci/conan/build_and_test.sh archives/c/curtain/0.3
  # 预期：L0/L1/L1e/L2/L5 PASS

  # 真机功能验证
  hdc install -r entry-default-signed.hap
  hdc shell aa start -b com.kasumizawamiyuu.curtainhost -a EntryAbility
  hdc shell uinput -M -g 3000 1000 1700 1000 800   # 右缘揭开
  hdc shell snapshot_display -f /data/local/tmp/curtain.jpeg
  ```
