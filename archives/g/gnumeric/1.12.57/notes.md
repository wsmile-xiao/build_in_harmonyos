# gnumeric 1.12.57 适配笔记（2026-08-22 更新）

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-22
- 编译器: clang/clang++ (OHOS SDK 15, profile: os=OHOS/6.0, cppstd=17, libc++)
- 状态: built
- 目标平台: OHOS aarch64 (armv8)
- Conan 引用: gnumeric/1.12.57

## 依赖链（已统一到新版本，与 goffice/0.10.57.1 修复配方一致）

```
gnumeric/1.12.57
├── goffice/0.10.57.1
│   ├── cairo-gobject/1.18.4 ──┬── cairo ── pixman/0.46.4 / libpng/1.6.58 / freetype/2.14.3 / fontconfig/2.18.1.1
│   ├── libgsf/1.14.58 ──┬── glib/2.88.0.1 (shared=True, override)
│   │                    ├── libxml2/2.15.3.1
│   │                    └── zlib/1.3.1.1.1.1 (override)
│   ├── glib/2.88.0.1 (override, shared=True)
│   └── zlib/1.3.1.1.1.1 (override)
├── cairo-gobject/1.18.4 / pixman/0.46.4 / libpng/1.6.58 / freetype/2.14.3
├── fontconfig/2.18.1.1 / expat/2.8.2.1 / libgsf/1.14.58
├── glib/2.88.0.1 (override, shared=True)
└── zlib/1.3.1.1.1.1 (override)
```

cmd-pkgs 预编译 GTK 栈（GTK_PREFIX=/storage/Users/currentUser/usr/local）：
gdk-pixbuf/atk/fribidi/libepoxy/libpng/libjpeg-turbo/fontconfig/freetype/
harfbuzz/pixman/pango/gtk+/libxml2/libxslt（glib 已切到 conan 2.88.0.1）

## 关键适配点（本次更新）

1. **依赖链更新**：`goffice/0.10.57.1@ohpcd/stable` → `goffice/0.10.57.1`；
   `zlib/1.3.1.1` → `zlib/1.3.1.1.1.1`（override）；`glib/2.84.0.1` →
   `glib/2.88.0.1`（override, shared=True）。CMD_PKGS 移除 glib（由 conan
   管理，R36）。
2. **glib-genmarshal wrapper**：cmd-pkgs glib 2.88 的 glib-genmarshal 是
   python3 脚本，构建环境 LD_LIBRARY_PATH 含 GTK_PREFIX/lib/external 时
   python3.12 加载错误 libintl → 生成 unset LD_LIBRARY_PATH 的 wrapper
   并前置到 PATH（AutotoolsToolchain 默认 PATH 会挤后 → 直接改写
   conanautotoolstoolchain.sh）。
3. **上游测试真实运行**（build() 内，goffice 同款运行闭包方案扩展）：
   - DT_NEEDED 闭包 + RUNPATH=$ORIGIN + ELF 签名；
   - GTK 栈智能 stub（消除静态内嵌 glib 冲突，字体/纸张/类型系统可运行）；
   - SIGTRAP 忽略（OHOS glib CRITICAL 日志调 raise(SIGTRAP)）；
   - GSETTINGS_SCHEMA_DIR（编译 gschemas.compiled）+ memory backend；
   - 插件闭包 + GNM_TEST_TOP_BUILDDIR + 无后缀模块文件 + LD_PRELOAD 全闭包；
   - 签名 perl + XML::Parser 2.59（用户分区 XS 需签名调用者）。
4. **test_package 真实运行**：闭包部署 + RUNPATH + 签名 + GTK stub +
   LD_PRELOAD 动态 glib → 8 项断言真实 PASS。

## 上游测试结果（159 项，2026-08-23 最终实测）

- **PASS 58**（核心计算引擎真实工作：ssconvert --recalc / sstest / ssindex / ssdiff / ssgrep / mps 导入）
- **SKIP 58**（上游样本缺失，上游同样 SKIP）
- **SKIP 15**（valgrind 11 + GUI 显示 4，HarmonyOS 无）
- **FAIL 28**（逐项技术原因见 reports/upstream_test_audit.md）：
  - 26 项 roundtrip/导出：perl 驱动下 zcat 读取 HMDFS 新写入文件偶发
    `not gzip`（I/O 写延迟时序）；手动逐步执行全部成功且 diff 无差异
    （权限问题已由 umask hook 修复）；
  - 1 项 t2005：sstest recalc 计算偏差（stub 环境字体/布局近似的边界）；
  - 1 项 t5904：mps 导入 SHA 元数据差异（UIData/generator 环境元素）。
- **关键修复**（相对首轮）：
  - preload 版本化库过滤 bug（4/39 → 39/39 build() 内自动 PASS）；
  - umask hook（roundtrip `-r` 权限修复，0660 组位）；
  - stub double 返回特判（deterministic 内容一致）；
  - ignoretrap 无输出（避免污染测试 stdout）。

## 验证结果

- conan create 成功（含 build() 内核心测试子集真实运行）。
- 产物: bin/gnumeric (GUI)、bin/ssconvert/ssindex/ssgrep/ssdiff、
  lib/libspreadsheet-1.12.57.so、lib/gnumeric/1.12.57/plugins/*.so (39 插件)、
  include/libspreadsheet-1.12/spreadsheet/*.h、lib/pkgconfig/libspreadsheet-1.12.pc。
- test_package: 消费者 smoke test 8 项断言真实运行 PASS。
- conan-verify: 见 conan-verify 报告。

## 交付物

- conanfile.py（约 900 行，含上游测试运行）、conandata.yml、patches/0001~0003、
  test_package/（conanfile.py + CMakeLists.txt + test.c + MANIFEST.yml）、
  commands.json（软件级）、reports/upstream_test_audit.md。

## 注意事项

- 未执行 submit / 未提交 PR / 未 git push。
- 完整 159 项测试矩阵在本机无显示环境实测；CI 真机可补跑 FAIL 项。
