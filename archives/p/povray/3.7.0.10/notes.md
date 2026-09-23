# povray 3.7.0.10 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-03}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 2026-09-03 探索期笔记

### 工具链问题 1：prebuild.sh 的 aclocal 报 AM_INIT_AUTOMAKE 未定义
- 现象：`unix/prebuild.sh` → bootstrap → `aclocal -I .` 后 autoconf 报 `configure.ac:169: error: possibly undefined macro: AM_INIT_AUTOMAKE`
- 根因：/usr/local 的 automake 1.16.5 安装破损，aclocal 内部调用 autom4te 用的是未替换占位符 `@am_AUTOM4TE@`（`sh: @am_AUTOM4TE@: inaccessible or not found`）
- 修复：`export AUTOM4TE=autom4te`（aclocal 优先读 AUTOM4TE 环境变量；autom4te 2.72 位于 /data/service/hnp/bin）后重跑 prebuild.sh 成功
- **CI 配方必须注入 AUTOM4TE 环境变量**（CI 若同款 automake 则同样触发）

### init-build 嵌套源码误判
- ohc-run.py init-build 的嵌套源码检测把 povray 内嵌的 libraries/ilmbase（vendored Windows 库，自带 configure）误判为源码根并"提升"
- 手工修复：rm -rf 错误的 .orig/.work → 从 tarball 重新解包（sha256 7bee83d9296b98b7956eb94210cf30aa5c1bbeada8ef6b93bb52228bbc83abff 校验通过）

### 依赖选型：boost 版本偏离（W0 计划 1.84.0 → 实际 1.90.0.4）
- ohpcd 的 boost/1.84.0 二进制只含 4 个静态库（filesystem/iostreams/program_options/regex），**无 libboost_thread**——povray AX_BOOST_THREAD 硬性要求无法满足
- boost/1.91.0 有 libboost_thread.so 但头文件被裁剪（158 个，缺 flyweight.hpp——povray source/backend/lighting/subsurface.h 必需），首编报 fatal error: 'boost/flyweight.hpp' file not found
- **定案 boost/1.90.0.4**（package_id 22b8e4fc）：308 个头文件（含 flyweight）+ 12 个静态库含 libboost_thread.a，两者兼得；povray 要求 boost>=1.37 满足
- libpng/1.6.39 + zlib/1.3.1 按计划不变（png 包提供 libpng.so/libpng16.so，-lpng 可解析）

### E129 umask 命中（configure 写 config.status 阶段）
- 现象：config.status 报 `./confXXXXXX/subs1.awk` 写入被拒（autoconf 2.72 产物在 mktemp 目录用 umask 077，HMDFS setgid → drwx--S--- 阻塞写入）
- 修复：`sed -i 's/umask 077/umask 022/g' configure config.status` 后重跑 config.status 成功（E129 知识库方案，与 polyglot 先例同款）

### C++ 标准定案：-std=gnu++11
- 源码扫描：auto_ptr（2 文件）/ register（11 处）/ throw() 动态异常规范（10 处）——C++17 下全报错
- gnu++11 下全部 deprecated-but-available（仅 warning），零源码补丁
- configure 透传路径验证：CXXFLAGS 用户参数在 configure.ac 结尾 `CXXFLAGS=\`echo $CXXFLAGS $pov_save_cxxflags\`` 追加，最终 Makefile CXXFLAGS = -pipe -Wno-multichar -Wno-write-strings -O3 -ffast-math -std=gnu++11

### E127 boost-musl：未触发
- boost/1.90.0.4 的 smart_ptr 已无 pthread_setcancelstate 引用（boost 1.90 上游已移除该路径），独立 smart_ptr 编译运行测试通过，无需 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏

### 编译结果（探索期，2026-09-03 20:10）
- make -j20 全量 154 个对象文件，0 error（85 warnings 属 deprecated auto_ptr/register 提示）
- 产物：unix/povray（ELF arm64 musl 动态链接，3.4MB）+ source/libpovray.a + vfe/libvfe.a
- `--version` banner 正常（含 "Persistence of Vision Raytracer Pty. Ltd."）
- 渲染测试通过：camera+light+plane+sphere 场景（含 #include "colors.inc" 场景库）→ 64x64 PNG（魔数 \x89PNG + IHDR 64x64 + bit_depth 8 + color_type 2），渲染统计行 "Trace Time: ... (0.003 seconds)"

### configure 参数定案（配方固化用）
```
COMPILED_BY="OHOS PC Adaptation <dev@opendesk.local>" NON_REDISTRIBUTABLE_BUILD=yes \
  --with-boost=$BOOSTPKG --with-boost-libdir=$BOOSTPKG/lib \
  --without-openexr --with-libjpeg=no --with-libtiff=no \
  CXXFLAGS="-std=gnu++11" CPPFLAGS/LDFLAGS/LIBS 来自 AutotoolsDeps
```
- 禁用效果（configure 汇总）：jpeg/tiff/openexr 禁用（X11 也 disabled，OHOS 无 X 正合适）
- 注意：prebuild.sh（生成 configure）必须带 `AUTOM4TE=autom4te` 环境变量；configure/config.status 生成后需 sed umask 077→022（E129）
---

**编译结束**: 2026-09-03 21:10
**最终状态**: built

## 对话记录

### 对话 #1 — 探索编译（2026-09-03 19:55-20:13）
- prebuild 生成 configure（AUTOM4TE=autom4te 修复宿主 automake 占位符损坏）
- 首次 configure E129（umask 077）→ sed 修复 → boost/1.91.0 首编缺 flyweight
- 逐一探测 ohpcd boost 版本 → 定案 1.90.0.4 → make -j20 全量 154 对象 0 error
- `--version` banner + 64x64 PNG 渲染冒烟（PNG 魔数/IHDR/python3 校验）全过
- make check（biscuit.pov 320x240 上游渲染测试）RC=0，Trace Time 0.186s

### 对话 #2 — 配方化与验证（2026-09-03 20:15-21:30）
- conan-init → 手写配方（application + AutotoolsToolchain + tool_requires automake/1.18）
- conan-verify 首跑 G2 FAIL：test_package shutil.copy SameFileError（test_type=explicit
  下 test() 工作目录即 test_package/ 源目录）→ 改临时目录输出 → conan test 快速复验 PASS
- conan-verify 二跑 G0-G4 全 PASS（干净构建 154 对象 + make check + install + 12 项断言）
- finish：refresh-patch 误把 prebuild 生成物打成 30 个补丁（已清理，零补丁设计）；
  W3 本地 CI 模拟（setup.sh + build_and_test.sh --build=povray/* 强制重建）通过
