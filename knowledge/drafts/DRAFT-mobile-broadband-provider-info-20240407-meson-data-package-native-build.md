# DRAFT-mobile-broadband-provider-info-20240407-meson-data-package-native-build：纯数据 meson 包在鸿蒙PC真机原生构建的三坑：PATH 内 clang 探测仍报 ENOENT 需 CC/AR 显式绝对路径；--prefix=/ 才符合 Conan destdir 数据安装且 .pc 的 pkgdatadir 绝对前缀须重写为 pcfiledir 相对；上游 should_fail 用例在 meson test 汇总显示 EXPECTEDFAIL 属通过语义

> Status: **Draft**（待审核 promote）| severity: `2` | category: `meson|data-package|ohos|pkgconfig|conan` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-mobile-broadband-provider-info-20240407-meson-data-package-native-build.kv`

---

## 触发面

- trigger_tool: `meson|conan`
- phase: `configure|test|package`

**匹配关键词**：meson, data package, data-only, Unknown compiler, cc, gcc, clang, ENOENT, CC, AR, llvm-ar, MesonToolchain, cross file, native file, EXPECTEDFAIL, should_fail, prefix=/, pkgdatadir, pcfiledir, apns-conf.xml, xsltproc, xmllint, serviceproviders.xml, ModemManager, NetworkManager

## 错误签名（error_signature）

```text
Unknown compiler\(s\): \[cc, gcc, clang|EXPECTEDFAIL: check-blanks|pkgdatadir is not the pcfiledir-relative contract|Sanity check compiler command line.*clang.*exit status 1
```

## 根因（root_cause）

①上游 meson project(..., 'c') 让纯数据包也强制走编译器+静态链接器探测。真机裸 meson：/data/service/hnp/bin 在 PATH 且 clang/ar 均可执行，但探测子进程对 cc/gcc/clang/llvm-ar 仍报 ENOENT（spawn 失败而非版本探测失败）；裸构建解决是 setup 前显式注入 CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar 绝对路径。conan 化后 CC 由 profile tools.build:compiler_executables 经 MesonToolchain machine file 注入（编译器探测过），但 ar 不在 compiler_executables 默认键里，meson 退回 PATH 找 llvm-ar/ar——Popen 直接 spawn（shell=False）的 PATH 搜索在本机对这些 hnp 符号链接条目报 ENOENT（shutil.which/which 命令都能找到，exec 搜索失败，conanbuild env PATH 值本身正确）；解决是 recipe generate() 里 shutil.which("llvm-ar") or shutil.which("ar")（兜底 /data/service/hnp/bin/llvm-ar、/data/service/hnp/bin/ar）写入 tc.binaries["ar"]，让 machine file [binaries] ar='<绝对路径>' 绕开 PATH 搜索。②数据包安装必须 --prefix=/：配方 Meson.install() 用 meson install --destdir=<package_folder>，上游 meson.install_dir 基于前缀拼接，prefix=/ 才得到 <pkg>/share/... 平铺布局（与 package_type="unknown" + resdirs=["share"] 对齐）；用真实前缀（如 /usr/local）会在包内嵌套绝对前缀目录，W2 结构校验直接失败。另外上游 mobile-broadband-provider-info.pc 把 pkgdatadir 硬编码为绝对前缀路径，设备侧 pkg-config --variable=database 消费会拿到断链路径，package() 必须把 pkgdatadir 重写为 ${pcfiledir}/../mobile-broadband-provider-info 相对契约。③上游 check-blanks 测试声明 should_fail: true（grep 命中缩进违规才算"失败"，当前数据无违规 → grep exit 1 → meson 报 EXPECTEDFAIL）；meson test 汇总与退出码把 EXPECTEDFAIL 计入通过（总体退出码 0），人工复核测试日志时勿把 EXPECTEDFAIL 行误判为失败用例。

## 影响范围（affected_scope）

鸿蒙PC真机（aarch64）上用 Conan+Meson 适配无编译产物的数据包（provider DB / ISO codes / hwdata 类）：project() 声明了 c 语言但不产二进制、.pc 含绝对 pkgdatadir、meson 测试含 should_fail 语义。mobile-broadband-provider-info 20240407 实测全覆盖。

---

*本文件由 `knowledge/drafts/DRAFT-mobile-broadband-provider-info-20240407-meson-data-package-native-build.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
