# ayatana-ido 0.10.4 适配笔记

## 编译环境
- 构建系统: cmake (upstream CMakeLists.txt; conan-init 的 autotools 自动检测不适用)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 依赖: 对齐 gtk/3.24.43 依赖图, 避免版本冲突 (R36)
conan install --requires=glib/2.84.0.1 --requires=gtk/3.24.43 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -g=PkgConfigDeps

# 2. CMake 手动验证构建 (探索阶段)
cmake .. -DENABLE_TESTS=ON -DCMAKE_PREFIX_PATH=<gtest_prefix> \
  -DCMAKE_SHARED_LINKER_FLAGS="<pkg-config -L 列表>"
make -j4 && make install DESTDIR=<staging>

# 3. 配方验证
python3 scripts/ohc-run.py conan-verify ayatana-ido 0.10.4   # 8 道门禁全过
python3 scripts/ohc-run.py finish ayatana-ido 0.10.4 published  # W3 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create source() 报 BadZipFile | codeload URL 无 `.tar.gz` 后缀, conan get() 无法识别格式 | conandata.yml 显式声明 `filename: ayatana-ido-0.10.4.tar.gz` (复用 E276) |
| 2 | 链接缺传递依赖库 (jpeg/zstd/cairo-gobject 等) | 上游只链接 `${PROJECT_DEPS_LIBRARIES}` 未用 `_LIBRARY_DIRS`, 传递 -L 全丢 | generate() 遍历 dependencies 注入全部 libdir (E429 草稿) |
| 3 | idotypebuiltins.h 生成失败 (glib-mkenums: No such file) | /data/service/hnp/bin/glib-mkenums 是断链符号链接, find_program 缓存坏路径 | tc.variables["GLIB_MKENUMS"] 显式指向 glib 包内真实脚本 (E543 草稿) |
| 4 | test_package 链接缺 g_libintl_ngettext | glib 包 glib-2.0.pc Libs 无 -lintl | test_package generate() 对 .pc 追加 -lintl (同 gtk 先例) |
| 5 | test_package 运行 cannot open display | 无头环境无 X11/Wayland | 启动 gtk 自带 broadwayd + GDK_BACKEND=broadway (复用 E463/E471/E527) |
| 6 | L5 soname_gate 拦截 | 上游 VERSION 0.0.0 SOVERSION 0 未产出 DT_SONAME | 显式注入 `-Wl,-soname,libayatana-ido3-0.4.so.0` |

## 源码修改

本轮无源码补丁 (patches/ 为空); 全部适配在配方 generate()/build()/test_package 内完成。

## 依赖版本

- glib/2.84.0.1 (transitive_headers/libs)
- gtk/3.24.43 (transitive_headers/libs)
- 传递: cairo/1.18.4, cairo-gobject/1.18.4.2, pango/1.50.14.1.1, gdk-pixbuf/2.44.6.1,
  harfbuzz/14.2.0.1.1.1, atk/2.38.0.1.1, libepoxy/1.5.10, fribidi/1.0.16 等
- 测试: gtest/1.17.0 (上游 gtest-menuitems 构建用)

## 验证结果

```bash
# 上游测试 (gtest-menuitems, broadway 无头后端): 4 独立 TEST_F / 4 通过 = 100%
./tests/gtest-menuitems --gtest_color=no   # [ PASSED ] 4 tests

# HarmonyOS 专项测试 (ohos-test/test_ido_ohos.c): 6 项检查 / 6 通过
./test_ido_ohos                            # == 结果: 全部通过 (失败 0) ==

# 配方验证 + 消费者测试
conan-verify: G0-G4 + L2/L4/L5 全过
conan create (test_package): ctest 1/1 PASS, test_ayatana-ido: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 版配方 (依赖注入 + SONAME + glib 工具路径) |
| conandata.yml | 官方 GitHub tag 源码 + 实测 sha256 + filename |
| test_package/ | pkg-config 链路消费者测试 (broadwayd 无头运行) |
| reports/knowledge-candidate-ledger.md | 知识候选台账 (路径 B 判定) |
| knowledge/drafts/E429-draft-*.kv/.md | CMake 传递 -L 注入模式 (路径 B) |
| knowledge/drafts/E543-draft-E556.kv/.md | find_program 断链符号链接绕过 (路径 B) |

## 注意事项

- 版本号 0.10.4 为上游版本 (首次适配, 无修复后缀)。
- 库无显示后端依赖, 消费方自行决定 GDK 后端; broadway 已验证可实例化。
- gtest-menuitems 上游测试需 ENABLE_TESTS=ON 单独构建 (配方默认 OFF)。
---

**编译结束**: 2026-09-03 14:48
**最终状态**: built
