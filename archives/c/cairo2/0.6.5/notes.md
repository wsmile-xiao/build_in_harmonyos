# cairo2 0.6.5 适配笔记

## 软件说明
cairo2 是 Cairo 2D 矢量图形库的 OCaml 绑定（上游 https://github.com/Chris00/ocaml-cairo）。
版本 0.6.5，dune 构建，语言为 OCaml + C stubs（src/cairo_stubs.c）。

## 依赖（W0 检查）
- ocaml/4.14.1.1.4：制品仓已有（tool_requires）
- dune/3.17.0：制品仓已有（tool_requires）
- cairo/1.18.4.2、freetype/2.14.3、fontconfig/2.18.1.1：制品仓配方已有

## 关键适配点

| # | 问题 | 根因 | 方案 |
|---|------|------|------|
| 1 | dune-configurator 库缺失 | 制品仓 dune 包只含 dune 二进制（lib/dune 仅 META/dune-package/opam），无编译好的 dune-configurator | 补丁 0001-src-dune.patch 移除 src/dune 中 discover 规则；conanfile.build() 直接生成 src/c_flags.sexp、c_library_flags.sexp、cairo_ocaml.h（含 OCAML_CAIRO_HAS_FT 1） |
| 2 | freetype/fontconfig 制品仓二进制拉取异常（conan download 0 命中） | cnb.cool 搜索 API 不完整（R35），且本地缓存修剪 | `conan install --build=<pkg>/*` 本地构建（freetype/fontconfig），package_id 与制品仓一致 |
| 3 | freetype 头文件路径特殊 | freetype 头在 include/freetype2/（且 ftmodapi.h 需 include/freetype2/freetype/） | c_flags.sexp 同时加入两级 include 路径 |
| 4 | OCAMLLIB 陈旧路径 | conan 缓存重定位后 ocamlc -where 失效（pdfsandwich E 同源） | 从 `which ocamlc` 推导 OCAMLLIB（pdfsandwich 同款 shell 表达式） |
| 5 | dune install 不可用 | HMDFS 上 dune 向上扫描 /storage/Users 报 Operation not permitted | 不用 dune install；package() 从 _build/install/default/lib realpath 实拷贝 |
| 6 | 包内符号链接断裂 | dune 安装树是指向 _build 的符号链接，conan copy 不解引用 | package() 用 os.path.realpath + shutil.copy2 拷贝真实文件 |

## 上游测试（R51 三步法）
- 清点：tests/dune 注册 7 个可执行测试（image_create, matrix_set, surface_gc,
  test_for_stream, test_finish, test_path, test_exn），另有 tests-gtk（依赖 GTK，无环境不跑）
- 运行：`dune runtest` 于本机（aarch64 鸿蒙PC 真机），exit 0，无 error/fail
- 通过率：**7/7 = 100%**（tests-gtk 因 GTK 依赖不在适配范围，属上游 depopt 之外的 GUI 示例）

## Conan 验证
- conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing：构建通过
- test_package：ocamlopt 链接 cairo.cmxa + libcairo_stubs.a，绘制/写出/读回 PNG 冒烟 OK

## 输出说明
- 包内 lib/cairo2：META、cairo.{cma,cmxa,cmxs,cmi,cmx,cmt,cmti,ml,mli,a}、
  cairo_ocaml.h、libcairo_stubs.a、dune-package、opam
- lib/stublibs/dllcairo_stubs.so：C stubs 动态库
- 消费方式：OCaml 项目以 ocamlfind/ocamlopt -I <prefix>/lib/cairo2 cairo.cmxa 链接
---

**编译结束**: 2026-09-26 09:37
**最终状态**: built
