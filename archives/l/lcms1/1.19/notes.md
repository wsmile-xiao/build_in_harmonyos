# lcms1 1.19 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-13
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify 8 道门禁已通过，未 upload）

## 编译步骤

```bash
# Step 1: init-build（官方 SourceForge 源）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build lcms1 1.19 \
  --url="https://downloads.sourceforge.net/project/lcms/lcms/1.19/lcms-1.19.tar.gz"

# Step 2: 手动编译
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check   # 全部通过（Success）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | lcms 1.19 自带 config.guess（2006 版）无 HarmonyOS 检测分支（知识图谱 E007） | 用 patch-autotools-ohos.pl 修补 config.guess（加 HarmonyOS 识别分支）；config.sub 版本过老补丁未生效，手动补 3 处（KERNEL-OS 组合列表、OS 列表、内核列表均加 linux-ohos） |
| 2 | config.guess 分支匹配后未输出直接退出 | HarmonyOS 分支设置 GUESS 后无 `echo; exit`，继续走编译探测路径 | 在 HarmonyOS 分支补 `echo "$GUESS" ; exit ;` |
| 3 | config.status: can't create ./confXXXXXX/out: Permission denied | HMDFS 文件系统 umask 077 临时目录对当前进程不可写（知识图谱 E011） | 按 E011 推荐：configure 中 `umask 077` → `umask 022` |
| 4 | configure 检测 TIFF/JPEG 可选支持 | lcms 1.19 可选依赖 libtiff/libjpeg（制品仓已发布但 configure 未启用） | 核心库无硬依赖，不启用可选支持，不影响交付 |

## 源码修改

探索阶段按 R3 只改源码不生成 patch（补丁由 finish 的 refresh-patch --auto 生成）：
- `config.guess`：新增 HarmonyOS 系统识别分支 + `echo "$GUESS"; exit`
- `config.sub`：新增 `linux-ohos` 三元组支持（3 处）
- `configure`：`umask 077` → `umask 022`（HMDFS 平台限制，E011）

## 依赖版本

无硬依赖。可选依赖 libjpeg（v10）/ libtiff（4.7.2）已发布制品仓，本包未启用。

## 验证结果

```bash
make check
# testbed/testcms：main() 实际调用 26 个测试函数（CheckEndianess/CheckSwab/CheckQuickFloor/
# TestFixedPoint/TestFixedScaling/TestJointCurves/TestReversingOfCurves/
# TestLinearInterpolation/TestReverseLinearInterpolation/Test3D/TestMatrixCreation/GetInfoTest/
# Test_sRGB/RealProfilesTest/TestInducedError/TestPreview/TestMultiprofile/
# TestLinearizationDevicelink/TestDeviceLinkGeneration/TestLinearizationDevicelink2/
# TestInkLimiting/TestSaveToMem/TestNamedColor/TestIT8/TestPostScript/TestColorantTableTag）
# 全部通过，最终输出 "Success."，退出码 0
# 通过率: 26/26 (100%)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，静态默认，system_libs=m） |
| conandata.yml | 源码 URL + SHA256（80ae32cb...） |
| test_package/ | 消费者测试（sRGB profile + RGB->Lab 变换）+ MANIFEST.yml |
| commands.json | 软件级工具声明（R38：含 icc2ps/icclink/icctrans/wtpt 可执行文件） |

## 注意事项

- 构建产物含 4 个可执行文件（icc2ps/icclink/icctrans/wtpt），已按 R38 声明 commands.json
- 库名为 `lcms`（liblcms.so/liblcms.a），非包名 lcms1
- config.guess/sub 为 2006 老版本，知识图谱 E007 命中并处理
---

**编译结束**: 2026-08-13 12:11
**最终状态**: built
