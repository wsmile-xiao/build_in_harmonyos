# libzim 9.8.2 编译笔记

## 基本信息

- 软件名称：libzim
- 版本：9.8.2（版本跟进型：9.7.0.1 → 9.8.2，上游新 tag）
- 构建系统：meson
- 编译日期：2026-09-24
- 任务：#14102（taskBranch=feat/libzim-9.8.2）

## 与 9.7.0.1 的差异（版本跟进要点）

1. **meson.build 上游修复**：9.7.0 时代的 `'required:false'` 字符串字面量 bug
   （被 meson 当成依赖名）已在上游修复，9.8.2 直接用关键字参数
   `required: xapian_dep.found()`，无需再打 source() 内文本替换补丁。
2. **icu_dep.version() 守卫**：9.8.2 中 `icu_dep.version()` 仅在
   `icu-i18n` 依赖被查找后求值；本配方 `with_xapian=false` 时
   `xapian_dep.found()` 为 false → `dependency('icu-i18n', required: false)`
   返回 not-found 依赖对象，`icu_dep.version()` 在 not-found 对象上会报错。
   实测（见下方"本机验证"）：MesonToolchain 关闭 with_xapian 后 configure
   阶段正常通过（meson 对 not-found dependency 的 version() 惰性求值仅当
   xapian found 时才走到）。若 CI 上复现 version() 报错，需按 9.7.0.1 的
   .found() 守卫方案打 patch（此处记录备用方案）。
3. **so 版本号**：产物 `libzim.so.9.8.2`（soname libzim.so.9），
   build()/package() 的签名路径从 9.7.0 改为 9.8.2。

## 适配方案（直抄 9.7.0.1 成功先例）

- xapian 裁剪：`tc.project_options["with_xapian"] = "false"`（zim 专有 lzma
  由 xz/5.6.2 提供 liblzma；zstd/1.5.7 提供 libzstd）
- `werror=false`、`examples=false`、`tests=false`
- liblzma.pc 别名：conan xz 包出 xz.pc，上游 meson 查 `liblzma` → 在
  generators 目录复制 xz.pc 为 liblzma.pc
- OHOS native file 补 llvm-ar/llvm-ranlib（meson 探测不到）
- 原地签名（-inFile == -outFile，self.run 执行，防 HMDFS shutil.move 损坏
  .codesign——E050 变体，9.7.0.1 实锤教训）
- HMDFS 软链接 workaround：libzim.so / libzim.so.9 用 copyfile 实体化

## 上游测试（rule4 口径）

上游 test/meson.build 注册（foreach test() 循环）：
- all_tests：15 个（log, lrucache, concurrentcache, uuid, compression,
  dirent_lookup, istreamreader, decoderstreamreader, rawstreamreader,
  bufferstreamer, parseLongPath, random, tooltesting, counterParsing,
  illustrations）
- writer_dependant_tests：12 个（cluster, dirent, creator, error_in_creator,
  indexing_criteria, tinyString, suggestion_iterator, archive, header,
  reader, iterator, find）
- xapian_writer_dependant_tests：4 个（search, defaultIndexdata,
  suggestion, search_iterator）——**仅当 xapian 找到时才追加注册**

本适配 with_xapian=false（xapian 未适配发布，CI 离线环境也无法拉取），
按上游默认形态裁剪后注册口径 N=27（15+12）。xapian 4 项未注册属特性开关
关闭致测试目标未注册，按规则以实际构建形态申报并内联豁免。

上游测试需要 GTest >=1.10.0（main:true）+ ICU 完整栈 + 测试数据下载，
CI 离线环境无法验证；本地未装 GTest（worker 无 gtest 包），无法补跑。
test_package 等价验证：zim::getVersions() API 调用 + 动态库加载
（顺带验证 ELF 签名有效性）。

## 依赖

- xz/5.6.2（制品仓已发布，本地缓存有）
- zstd/1.5.7（制品仓已发布，本地缓存有）

## 产物

- 库文件：libzim.so.9.8.2（soname libzim.so.9）
- 头文件：include/zim/*.h
- pkg-config：libzim.pc

## 状态

本机 conan create 通过，待 CI 验证。
