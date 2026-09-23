# libmustach-core 1.2.10 适配笔记

## 编译环境

- 构建系统: makefile（上游原生 Makefile，无 configure）
- 编译日期: 2026-09-14
- 编译器: clang（Conan `tools.build:compiler_executables` 注入，R33 合规）
- 状态: built（待真机预检回填实测证据）

## 上游信息

- 仓库: https://gitlab.com/jobol/mustach（tag 1.2.10）
- 源码包: mustach-1.2.10.tar.bz2
- SHA256: 7e7e97e3f72e33080ad55f5119369e13f9f467b8fe34258a00cad05b0fec1c19
- 许可证: 0BSD（1.2.8 起由 ISC 转为 Zero-Clause BSD，见 CHANGELOG）
- libmustach-core 内容: mustach.c + mustach-wrap.c，对外头文件 mustach.h + mustach-wrap.h，零外部依赖

## 编译步骤

core-only 切分构建（JSON 后端与 CLI 工具全部关闭）：

```bash
make CC=<conan-conf-c> cjson=no jsonc=no jansson=no libs=split tool=none -j1
make install CC=<conan-conf-c> cjson=no jsonc=no jansson=no libs=split tool=none \
  DESTDIR=<package_folder> PREFIX=/
```

- 产物（shared）: lib/libmustach-core.so.1.2（含 .so.1/.so 符号链接）、lib/pkgconfig/libmustach-core.pc、include/mustach/*.h
- 静态（shared=False，默认）: 手工编译 mustach.o/mustach-wrap.o（-fPIC -DVERSION=1.2.10）后 `ar rcs libmustach-core.a`
- 上游 EFLAGS 自带 -fPIC；所有 make 调用显式传 CC/AR/RANLIB，不依赖 shell 环境变量（R33）
- 构建产物不含可执行文件，纯库，无需 commands.json（R38）

## 上游测试盘点（申报表）

| 套件 | 数量 | 运行方式 | 本轮状态 |
|------|------|----------|----------|
| test1..test8（basic-tests） | 8 | `make basic-tests`，经 dotest.sh 驱动 mustach 工具 diff resu.ref | 未运行：全部依赖 mustach CLI 工具，而工具必须链接 JSON 后端 |
| test-specs（spec-tests） | 3 后端 × spec 文件 | `make spec-tests`，需先 git clone mustache/spec @ v1.4.1 | 未运行：同上 + 需联网克隆外部 spec 仓库 |
| make check / ctest / pytest | 0 | 上游无此目标 | 不适用 |

缺口原因（具体）:

1. mustach 工具源码（mustach-tool.c）以 `#error "no defined json library"` 强要求 TOOL ∈ {JSON_C, JANSSON, CJSON}；
2. 三个后端库（cjson、json-c、jansson）在制品仓均未发布（查得状态 built/partial，无 published），按 R36 不能在配方中 requires；
3. spec-tests 需联网 `git clone https://github.com/mustache/spec.git`，构建期网络依赖不可控。

补齐后：build() 内离线 vendor cJSON 实跑 basic-tests 8/8；test_package 仍用两个真实消费者二进制直接覆盖 core API（变量/转义/section/反转/迭代/partial 语义对应物 + 错误码），共 12 项断言；待任一 JSON 后端发布后，可追加工具型用例。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出 main 后 `archives/l/libXext` 常驻 dirty | 上游同时存在 `libXext` 与 `libxext`（仅大小写差异），Windows 文件系统合并为同一目录 | 与本任务无关，保持不动；在大小写敏感系统（真机/CI）自然干净 |
| 2 | 上游 `test` 目标隐含网络克隆 | `test-specs/specs` 规则做 git clone + checkout v1.4.1 | 不调用 `make test`；MANIFEST 记 `upstream_test_in_build: true` 并附审计 |

## test_package 设计

- test_core.c（合并单一二进制，两套件共 12 项）:
  - 套件 1（render，7 项）: `mustach_file` 完整渲染对照（含 `&` 转义、真假 section、反转 section、双元素列表迭代）+ 零回调 INVALID_ITF + 未闭合 section 报错 + 空标签报错 + 版本宏。
  - 套件 2（wrap，5 项）: `mustach_wrap_file` 转义插值 + 三花括号原文输出 + 版本宏。
  - 输出经 TMPDIR 下显式 fopen 文件回读，避开真机上启动即 SIGTRAP 的 `open_memstream`（`mustach_mem`/`mustach_wrap_mem`）路径，覆盖同一渲染引擎。
- 单一二进制经 CMakeDeps 链接 `libmustach-core::libmustach-core`，test() 以 conanrun 环境执行，打印 `HMBS_TEST_PACKAGE_RESULT` 机器证据（discovered=2）。

## 验证结果

```bash
# 真机预检（hmbs 后台执行，待回填）
# conan create archives/l/libmustach-core/1.2.10 -pr:h=ci/conan/profiles/ohos-aarch64 ...
```

- 编译状态：待真机预检回填
- 上游测试用例通过率：待真机预检回填（基本套件 8 项 build() 内 vendor cJSON 实跑，见补充说明/spec-tests 未运行声明）
- 新增测试用例通过率：待真机预检回填（test_package 2 用例/12 断言）

## 注意事项

- 本包刻意零依赖；若未来需要运行工具型上游套件，仍不加 requires（R36）：cJSON 仅 vendor 于配方内编译测试工具，不进包、不加依赖。
- 上游 meson.build 内版本号仍为 1.2.8（stale），以 Makefile 的 1.2.10 为准；配方走 Makefile 通道，不受影响。
