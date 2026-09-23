# E429: ohpcd libtool 制品把独立 libltdl 发行版装在 share/libtool/，libtoolize --ltdl 复制失败导致 autoreconf 终止

## 基本信息
- **严重度**: 2
- **类别**: autotools, conan, packaging
- **触发工具 / 阶段**: libtoolize|autoreconf / configuration
- **来源**: libprelude 5.2.0 适配（OHOS aarch64，PR 分支 feat/libprelude-5.2.0，Agent LPR5）
- **状态**: 草稿（未进 index.tsv，待主编 `graph promote`）

## 错误特征
```
libtoolize:\s+error: '.*share/libtool-conan/libltdl/.*' not found|autoreconf: error: .*libtoolize failed with exit status: 1
```

## 触发条件
- 构建系统: autotools（libtool 递归/内嵌 libltdl）或 conan/Conan 依赖图场景
- 阶段: configuration
- 平台: HarmonyOS OHOS aarch64（clang 15 / musl / HMDFS），Conan 2.29.1 + ohpcd 制品

## 根因分析
libtool/2.5.4 制品的 package() 把上游独立 libltdl 发行版（含 pregenerated configure、ltdl.c、loaders/、Makefile.in）装到 share/libtool/，而 libtoolize 查找 ltdl 的路径是 <pkgdatadir>/libltdl（该包里是 share/libtool-conan/libltdl，只剩头文件）→ LT_CONFIG_LTDL_DIR 声明的项目（libprelude、Gnumeric 等）无法用 libtoolize --ltdl 自举

影响范围：所有 configure.ac 里有 LT_CONFIG_LTDL_DIR 且归档无 configure 的项目（libprelude 5.2.0 实测）

## 解决方案

### 推荐方案（materialize-libltdl-from-libtool-package）
不跑 autoreconf；在 conanfile.build() 里依次执行 libtoolize -c --force --automake（忽略其 ltdl 复制失败）→ 从 tool_requires 的 libtool 包把 share/libtool 复制成源码树的 libltdl/ → 清掉 libltdl/Makefile.in 里未被替换的 @MAINTAINER_MODE_TRUE@ 字面量 → 手工跑 aclocal/autoconf/autoheader/automake 完成自举

### 验证命令
```
ls <libtool 包>/share/libtool/configure && (libtoolize -c --force --ltdl --automake; echo $?)
```

### 落地参考
archives/l/libprelude/5.2.0/conanfile.py

## 关键词
libtoolize, libltdl, share/libtool-conan, not found, autoreconf failed with exit status 1, LT_CONFIG_LTDL_DIR, ohpcd libtool
