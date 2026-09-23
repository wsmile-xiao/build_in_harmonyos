# DRAFT — zlib 同图版本 pin 冲突的依赖选项裁剪法（KDE Qt5 图像插件生态）

> 草稿状态：DRAFT（来源 kimageformats5 5.116.0 适配 PR #10894，作者 j669539）

## error_signature（可机器匹配）

```
ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph.
Conflict originates from libpng/1.6.58
```

## error_excerpt

```
ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph. Conflict originates from libpng/1.6.58
```

## root_cause（根因）

同一 Conan 依赖图中两个包对同一底层库 pin 了不同版本：qt5-qtbase 配方
`requires("zlib/1.3.1")`，而图像格式库生态（libavif→libpng/1.6.58、libraw
默认）pin zlib/1.3.1.1。Conan 2 的版本解析对同图同包不同版本引用是硬冲突
（非 range），install/create 直接失败。根本原因是上游配方各自锁死精确版本
而非 range，且 zlib 频繁出适配修复版（1.3.1.1、1.3.1.2...）导致新旧 pin
并存于生态——Qt5 系生态高发（qtbase 是最大 zlib pin 方）。

## rec_approach（解决方案：三步裁剪法）

1. **定位双链**：报错 "Conflict originates from X" 给出引入方，逐包查
   conanfile 的 requires 确认 pin 版本。
2. **选项重构**：冲突方若有功能开关可关（libraw 的 enable_zlib/
   enable_jpeg），置 False 后该包退出冲突链，`--build=missing` 源码构建
   该变体（本例 libraw 无 zlib 变体仍可解码 raw，read-raw 测试通过）：
   ```python
   default_options = {"libraw/*:enable_zlib": False, "libraw/*:enable_jpeg": False}
   ```
3. **整体裁剪**：关不掉的（libavif 无 zlib 开关）裁掉对应可选插件
   （KIMAGEFORMATS_HEIF/JXL=OFF），notes.md 记录结构约束与恢复条件。

禁止 --update/force 硬混版本（musl 下混链符号风险不可控）。

## fallback（兜底）

等上游统一 pin；或配方 fork 发布 X.Y.Z.N 后缀版本修正 requires
（仅关键依赖值得）。

## verification_cmd（验证命令）

```bash
printf '[requires]\nqt5-qtbase/5.15.2\nlibraw/0.22.1\n' > conanfile.txt
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... \
  -o "libraw/*:enable_zlib=False" -o "libraw/*:enable_jpeg=False"
# 预期: Install finished successfully（无 zlib 冲突）
# 功能完整性: kimageformats-read-raw CTest PASS（无 zlib 的 libraw 可解码 raw）
```

## verify_builds（构建验证）

- CI #51036 / 最新轮（kimageformats5 PR #10894，conan-build-test 全绿）
- 本地 conan create：12 插件全产出；上游测试 15/17 实跑通过（含 read-raw PASS）

## 价值判断（三问）

- 去掉库名仍有效吗？有效——任何"同图双 pin 同库不同版本"场景适用
  （Qt5/KDE 生态尤其高发：qtbase 是最大 zlib pin 方）
- 系统性还是本库专属？系统性——生态层结构约束
- 已有条目为何不覆盖？图谱 zlib 条目（E518/E533/E539/E540/E541）全是
  打包/链接/工具链主题，无版本 pin 冲突主题；E345 是元数据路径主题——
  查重零命中
