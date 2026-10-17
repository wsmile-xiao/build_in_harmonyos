# E610: LTDL_INIT([recursive]) 下父 configure 替换 libltdl/Makefile，LTLIBOBJS 恒空导致 libltdlc.a 缺 lt__argz.lo

## 基本信息
- **严重度**: 2
- **类别**: autotools, libtool, linking
- **触发工具 / 阶段**: ld|make|libtool / linking
- **来源**: libprelude 5.2.0 适配（OHOS aarch64，PR 分支 feat/libprelude-5.2.0，Agent LPR5）
- **状态**: 草稿（未进 index.tsv，待主编 `graph promote`）

## 错误特征
```
ld\.lld: error: undefined reference due to --no-allow-shlib-undefined: lt__argz_|llvm-nm.*libltdlc\.a.*U lt__argz
```

## 触发条件
- 构建系统: autotools（libtool 递归/内嵌 libltdl）或 conan/Conan 依赖图场景
- 阶段: linking
- 平台: HarmonyOS OHOS aarch64（clang 15 / musl / HMDFS），Conan 2.29.1 + ohpcd 制品

## 根因分析
LTDL_INIT([recursive]) 不触发 AC_CONFIG_SUBDIRS，libltdl/Makefile 由父项目 config.status 替换；而 libltdl 的 _LT_LIBOBJ 探测（argz/dirent/strlcpy）只在它自己的 configure 里跑，父项目 LTLIBOBJS 为空 → libltdlc.a 少了 lt__argz.lo，ltdl.o 里的 5 个 U lt__argz_* 未定义；libprelude.so 照常链接出厂，直到链接下游可执行文件（prelude-admin）才被 lld 的 --no-allow-shlib-undefined 抓住

影响范围：所有以 recursive 模式内嵌独立 libltdl 的 autotools 项目（libprelude 5.2.0 实测；musl/OHOS 上因 gnulib 未提供 argz 探测而暴露）

## 解决方案

### 推荐方案（switch-libltdl-to-subproject-mode）
给 configure.ac 打补丁：LTDL_INIT([recursive]) → LTDL_INIT([subproject])（触发 AC_CONFIG_SUBDIRS），并从顶层 AC_CONFIG_FILES 列表移除 libltdl/Makefile（否则与子配置冲突）；libltdl 跑自己的 configure 后 LTLIBOBJS 与 libltdl/config.h 均正确生成

### 验证命令
```
make -C <build>/libltdl >/dev/null; grep '^LTLIBOBJS' <build>/libltdl/Makefile; llvm-nm -A <build>/libltdl/.libs/libltdlc.a | grep -c ' U lt__argz'
```

### 落地参考
archives/l/libprelude/5.2.0/patches/0001-configure.ac.patch

## 关键词
LTDL_INIT, recursive, LTLIBOBJS, libltdlc.a, lt__argz, no-allow-shlib-undefined, undefined reference, AC_CONFIG_SUBDIRS, subproject
