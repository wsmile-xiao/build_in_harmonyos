# 上游测试台账 — imlib2 1.9.1（OHOS armv8 适配）r03 返工版

- 任务：imlib2-1.9.1-r03-pc4-23-20260917T064703Z（返工：源码来源切换为官方 sourceforge release 归档）
- r02 结论：31/31 配置可执行集合通过 + 8 例 X11 排除（用户裁决终态口径，不再追 39/39）
- r03 变更：conandata/conanfile source() 由 git clone(git.enlightenment.org) 切换为官方
  sourceforge release 归档（https://downloads.sourceforge.net/.../imlib2-1.9.1.tar.gz，
  sha256=c319292f5bcab33b91bffaa6f7b0842f9e2d1b90df6c9a2a39db4f24d538b35b，实测下载核验一致）；
  官方 release 归档不含 test/（上游 DIST_SUBDIRS 排除 git-only 测试套件），配方随
  export_sources 携带官方 git tag v1.9.1 同版本测试源（upstream-test/ -> test/），
  补丁 0005 使 configure.ac 无条件生成 test/Makefile。
- 测试源码：官方 release 归档 + 官方 git tag v1.9.1 test/（同版本官方测试源）
- 构建：conan create（os=OHOS, arch=armv8, clang 15, Release），`--enable-test`（补丁 0001）
- 运行：9 个非 X11 gtest 程序，env 含 IMLIB2_LOADER_PATH/LD_LIBRARY_PATH（依赖包 .pc 前缀）/TMPDIR/TMP/TEMP；
  test_file 在真实权限挂载点 /data/storage/el2/log（0700，chmod 生效）运行

## 双口径统计（r03 最终，与用户裁决一致）

| 口径 | 数值 | 说明 |
|---|---|---|
| source_declared_total | **39** | 官方 tag 源码 test/*.cpp 的 gtest TEST() 声明总数（10 个测试源文件；test.cpp 为公共 main，不计用例） |
| configured_executable_total | **31** | 当前 OHOS 配置（BUILD_X11=no）实际实例化的独立可执行用例数（9 个 gtest 程序；test_grab 8 例被 X11 互斥分支排除） |
| executed_passed_total | **31** | 实际执行并通过 |
| failed | **0** | — |
| uninstantiated | **8** | test_grab.cpp 8 例（`if BUILD_X11 GTESTS += test_grab` 上游互斥分支；X11 头/运行时缺失，恢复条件=具备 X11 环境） |

- 全量通过率（通过数/全量发现数）：**31/39 = 79.5%**
- 当前配置可执行集合通过率：**31/31 = 100%**

## 源码声明 → 构建条件 → 构建目标 → gtest 注册项 → 执行结果映射

| 测试源文件 | TEST 声明 | 构建条件 | 构建目标 | 注册项 | 结果 | 备注 |
|---|---|---|---|---|---|---|
| test_misc.cpp | MISC.version / MISC.strerror | — | test_misc | 2 例 | **2/2 通过** | R01 已过 |
| test_string.cpp | STR.strsplit_1..4 | — | test_string | 4 例 | **4/4 通过** | R01 已过 |
| test_file.cpp | FILE.file_extension / file_exists / file_is_file / file_is_dir / file_can_read / file_is_real_file / file_key | — | test_file | 7 例 | **7/7 通过** | file_can_read 修复：真实权限挂载点 + TMPDIR（HMDFS chmod 无效→0700 chmod 生效目录） |
| test_context.cpp | CTX.ctx | — | test_context | 1 例 | **1/1 通过** | R01 已过 |
| test_load.cpp | LOAD.load_1 / LOAD.load_2 | — | test_load | 2 例 | **2/2 通过** | 修复：启用全部 loader（jpeg/tiff/webp/gif/id3/bz2/lzma）+ SRC_DIR 相对化（out-of-tree srcdir 破坏 "../"+IMG_SRC symlink 构造） |
| test_load_2.cpp | LOAD2.load_1 | — | test_load_2 | 1 例 | **1/1 通过** | 修复：0002/0003 TMPDIR 补丁（/tmp 只读+loader 硬编码 /tmp）+ 0004 xpm 命名色内置表（无 rgb.txt）+ id3tag 桥接补 -lz |
| test_save.cpp | SAVE.save_1n_rgb / save_1p_rgb / save_1n_argb / save_1p_argb / save_2a_immed / save_2a_defer / save_2b_immed / save_2b_defer | — | test_save | 8 例 | **8/8 通过** | 修复：jpeg/tiff/webp/gif saver 依赖发布后启用 |
| test_scale.cpp | SCALE.scale_1_rgb / scale_1_argb | — | test_scale | 2 例 | **2/2 通过** | R01 已过 |
| test_rotate.cpp | ROTAT.rotate_1_aa / rotate_1_noaa / rotate_2_aa / rotate_2_noaa | — | test_rotate | 4 例 | **4/4 通过** | R01 已过 |
| test_grab.cpp | GRAB.grab_noof_s0..sd2 / grab_offs_s0..sd2（8 例） | `if BUILD_X11`（test/Makefile.am GTESTS += test_grab）；config.log BUILD_X11_FALSE=''（X11 构建关闭） | test_grab（未构建） | 未注册 | 未实例化（8 例） | 纳入尝试：clang++ -std=c++17 编译 test_grab.cpp → 首错 `X11/Xutil.h file not found`；且用例依赖 XOpenDisplay/imlib_create_image_from_drawable（X11 显示/抓屏），OHOS 无 X11 无法编译运行 |

## r01→r02 修复明细（10 例失败 → 0）

| 失败用例 | r01 根因 | r02 修复 | 恢复条件（若未修复） |
|---|---|---|---|
| FILE.file_can_read | HMDFS 忽略 chmod 000（E046），rc=1≠0 | 在 /data/storage/el2/log 等 chmod 生效挂载点创建 0700 目录，设置 TMPDIR/TMP/TEMP 后运行 test_file，复制 Makefile 满足 "./Makefile" 相对引用 | — |
| LOAD.load_1 / load_2 | out-of-tree 绝对 srcdir 使 symlink `../`+IMG_SRC 断裂 err=2 ENOENT；jpg/gif/id3/jpg.mp3/tiff/webp loader 未构建 | 全部可选 loader 依赖发布后启用；test/Makefile SRC_DIR 相对化 | — |
| LOAD2.load_1 | /tmp 只读 + decompress_load.c 硬编码 /tmp → ff.gz 失败；jpg.mp3：id3.so 缺 zlib 符号 + loader_id3 硬编码 /tmp；xpm：命名色 white 无 rgb.txt 解析失败 | 0002 TMPDIR 补丁（decompress/loader_id3）；id3tag 桥接 .pc 追加 -Lzlib -lz；0004 内置常用颜色名表 | — |
| SAVE.save_1n_rgb / save_1p_rgb / save_1n_argb / save_1p_argb / save_2b_immed / save_2b_defer | jpeg/tiff/webp/gif saver 未构建（依赖未适配发布） | 依赖发布终态复核（libjpeg/10、libtiff/4.7.2、giflib/6.1.3、libwebp/1.6.0、libid3tag/0.16.3、bzip2/liblzma conan download 全部实例可下载）后启用 | — |

## 依赖发布终态复核（最终回报前，R35 用 conan download 实测）

| 依赖 | 版本 | 查询命令 | 退出码 | 时间 | 结果 |
|---|---|---|---|---|---|
| libjpeg | 10 | conan download libjpeg/10 -r=ohpcd | 0 | 2026-09-17T03:56:29Z | 二进制可下载 |
| libtiff | 4.7.2 | conan download libtiff/4.7.2 -r=ohpcd | 0 | 2026-09-17T03:57:01Z | 二进制可下载 |
| giflib | 6.1.3 | conan download giflib/6.1.3 -r=ohpcd | 0 | 2026-09-17T03:57:02Z | 二进制可下载 |
| libwebp | 1.6.0 | conan download libwebp/1.6.0 -r=ohpcd | 0 | 2026-09-17T03:57:04Z | 二进制可下载 |
| libid3tag | 0.16.3 | conan download libid3tag/0.16.3 -r=ohpcd | 0 | 2026-09-17T03:57:05Z | 二进制可下载 |
| bzip2 | 1.0.8.2 | conan download bzip2/1.0.8.2 -r=ohpcd | 0 | 2026-09-17T03:57:06Z | 二进制可下载 |
| liblzma | 5.8.1 | conan download liblzma/5.8.1 -r=ohpcd | 0 | 2026-09-17T03:57:08Z | 二进制可下载 |

## 分类汇总（发现 39 例全量口径）

- 通过：31 例（79.5%）——当前配置可执行集合 31/31（100%）
- 未实例化：8 例（20.5%），test_grab X11 互斥分支（上游明确排除条件 + 编译/runtime 双向验证）
- 失败：0 例

注：`test/` 目录其余文件（test.cpp=公共 main、test.h、images/ 资源、Makefile.am）为框架/资源，非独立用例；所有数字均有命令、退出码与日志支撑（logs 见 $TMPDIR/imlib2-tests-r02final/，运行命令为各 test_* 直接执行，cwd 见台账）。