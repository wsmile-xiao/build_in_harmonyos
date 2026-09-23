# E549 草稿：上游测试依赖 freedesktop 共享数据库（mime/tzdata）缺失——tool_requires 测试期注入配方化

> 来源：kfilemetadata 6.28.0 适配（PR #8700 审核打回修复轮，commit c32ced04b9）；
> 复用 kcalendarcore 6.26.0（PR #8667）tzdata 注入先例。
> 状态：pending-editor-review（拟提升编号 E549，最终由主编确认）

## 错误特征

上游测试套件依赖 freedesktop 共享数据库（mime/zoneinfo 等），OHOS 系统未携带，测试在"库功能完全正常"的前提下大面积失败：

- **mimetype 类**（QMimeDatabase 消费者）：
  - `'plugin.mimetypes().contains(mimeType)' returned FALSE.`（测试夹具先按 mimetype 找提取器插件，找不到直接 FAIL）
  - 识别退化特征：文件被识别为泛型类型，如 `test.kra → application/zip`、`test.ape → audio/x-mod`
  - `QMimeXMLProvider: MimeType is ambiguous between application/epub+zip and application/zip`
  - 受影响测试可占全套 40%（kfilemetadata 26 项中 10 项）
- **时区类**（QTimeZone/localtime_r 消费者）：`system time zone undeterminable`（kcalendarcore #8667 实例）
- 复现命令：conan create 构建树内 `ctest --output-on-failure`

## 根因

1. **OHOS 无 /usr/share/mime、无 /usr/share/zoneinfo**：QMimeDatabase 默认只保留 Qt 编译进二进制的极小 mime 子集（几十种），shared-mime-info 数据库（freedesktop.org.xml，~3000 条 mimetype 定义）整体缺失；命名时区解析同理。
2. **失败语义误导**：失败点在"测试夹具按 mimetype 匹配插件"（`MimeUtils::strictMimeType`），不在被测库本身——看起来像包缺陷，实际是**测试环境缺数据资产**。
3. **证据链**（kfilemetadata 实例）：dump 工具实测注入前 `test.kra → application/zip`（KritaExtractor 注册 `application/x-krita`，contains 判定 FALSE）；注入 freedesktop.org.xml 后同一二进制 `test.kra → application/x-krita`，KritaExtractor 正常命中。

## 修复方案（配方化，可复制）

把"系统级共享数据库"当作**测试期数据资产**用 conan 包注入（不进消费者图、不进 package_id）：

1. **W0 先查制品仓数据包**：mime→`shared-mime-info/2.4`（含 `data/freedesktop.org.xml.in`）；时区→`tzdata/2026.3`
2. **build_requirements()**：`self.tool_requires("shared-mime-info/2.4")`
3. **_run_upstream_tests() 注入**：

```python
smi = self.dependencies.build.get("shared-mime-info")
if smi and smi.package_folder:
    smi_xml = os.path.join(smi.package_folder, "data", "freedesktop.org.xml.in")
    if os.path.isfile(smi_xml):
        mime_pkgs = os.path.join(self.build_folder, "share", "mime", "packages")
        os.makedirs(mime_pkgs, exist_ok=True)
        staged = os.path.join(mime_pkgs, "freedesktop.org.xml")
        if not os.path.isfile(staged):
            shutil.copy(smi_xml, staged)   # ⚠ 不能用 conan copy，见踩坑 2
        env.prepend_path("XDG_DATA_DIRS", os.path.join(self.build_folder, "share"))
# 时区变体（kcalendarcore 先例）：
#   test_env.define("TZDIR", zoneinfo_tree)
#   test_env.define("QT_ZONEINFO", zoneinfo_tree)
```

原理：QMimeXMLProvider 扫 `<XDG_DATA_DIRS>/mime/packages/*.xml`；QTimeZone 读 `TZDIR`/`QT_ZONEINFO`。

## 踩坑（两个非显然陷阱）

1. **conan 缓存双布局**：手工跑构建树测试收集 lib 路径时要同时扫 `/p/<前缀>*/p/lib`（直装布局）与 `/p/b/<前缀>*/p/lib`（build 布局），单扫一个会漏包（qtbase 在 /p/ 直下、kfilemetadata 自身在 /p/b/）；LD_LIBRARY_PATH 必须冒号分隔。
2. **conan.tools.files.copy() 单文件改名复制是静默 no-op**：`copy(self, "freedesktop.org.xml.in", <具体文件路径>, <目标文件>)` 的 pattern 在 src **目录**里按文件名匹配，src 传具体文件路径时目录枚举不到该条目——不报错、不产出目标文件；实测整轮 conan create 后暂存 XML 缺失、XDG_DATA_DIRS 指向空目录、测试结果纹丝不动（注入"生效"但通过率不变，排查到暂存目录为空才发现）。单文件直拷用标准库 `shutil.copy`；conan copy 只适合"目录内 pattern 批量复制"。（底层机制与 `DRAFT-ohos-conan-copy-fnmatch-anchored`（fnmatch 锚定匹配）同源：彼讲子目录产物 0 匹配，此为"src 传具体文件路径"触发形态，mime/tzdata 注入主题无重叠）

## 降级方案

数据包不在制品仓时：mime 类可在配方内打包最小 XML 子集（仅含被测库注册的 mimetype + glob/魔数定义，如 krita/ape 两条），或推动 shared-mime-info 入仓后再切包注入；均不可行时在 PR 正文按"环境限制"逐项豁免并保留失败明细（禁 stub/禁跳过断言）。

## 验证结果

- kfilemetadata 6.28.0：26 项上游测试 **15 过 → 23 过（58% → 88%）**，10 项 mimetype 类失败全部恢复
- conan create 干净构建全链复现（package_id `cf3a3334019959930b606987508405eee120183f` 不变——tool_requires 不影响包 id）
- CI #41899（PR #8700）
- 剩余失败与此无关（qtbase 无 ICU / exiv2 无 BMFF / OHOS xattr 语义，另案定性）

## 适用边界

- 适用于"测试夹具按系统共享数据库匹配/解析"的场景（mime/zoneinfo/icon-theme/desktop-entry 等 XDG 数据族）
- 不适用于库运行时自身强依赖系统服务的场景（那是 R40 深度适配边界）
