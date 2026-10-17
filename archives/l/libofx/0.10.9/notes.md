# libofx 0.10.9 适配笔记

## 编译环境

- 构建系统：cmake（上游双构建系统 autotools + cmake，本配方选用 cmake）
- 编译器：clang（Conan `tools.build:compiler_executables` 注入，R33 合规）
- 状态：built（待真机预检回填实测证据）
- 依赖：opensp/1.5.2（已在制品仓有归档，提供 SGML 解析核心 libosp）

## 上游信息

- 仓库：https://github.com/libofx/libofx（tag 0.10.9，2022-10-03）
- 源码包：https://github.com/libofx/libofx/archive/refs/tags/0.10.9.tar.gz
- SHA256：ea9fa07759622ecc7f25b637fa8fb34d587af80607ca4389d25966a6a4f94ab9
- 许可证：GPL-2.0-or-later
- 内容：OFX 银行协议解析库 + C API（inc/libofx.h），附带 ofxdump / ofx2qif / ofxconnect 三个 CLI 工具

## 构建配置抉择

- `-DENABLE_OFXCONNECT=OFF`：ofxconnect 需要 libcurl + libxml++-2.6（ABI 2.6，
  vcpkg 仅提供 ABI 5.0，上游 README 明确称暂无 workaround），制品仓亦无
  libxml++-2.6，故关闭该工具。configure.ac 中同样为可选（缺失时 warn 并跳过）。
- `-DENABLE_OFXDUMP=ON -DENABLE_OFX2QIF=ON`：两个工具仅链接 libofx，无额外
  依赖；保持开启可运行上游 ctest 套件。包内含可执行文件，属 tool+library
  混合包，软件级 commands.json 已声明（R38）。
- `-DENABLE_ICONV=ON`：编码转换支持；FindIconv 缺失时优雅降级（HAVE_ICONV
  置空），不阻塞构建。
- OpenSP 发现：generate() 从 `opensp/1.5.2` 依赖包内定位
  `ParserEventGeneratorKit.h` 与 `libosp.so/a`，写入
  `OpenSP_INCLUDE_DIR/OpenSP_LIBRARY` 缓存变量；同时生成 PkgConfigDeps，
  双通道保证上游 FindOpenSP 模块命中。
- 产物：库文件名为 `libofx.so`（上游 `PREFIX ""`），链接旗为 `-lofx`
  （libofx.pc.in 佐证：`Libs: -L${libdir} -lofx`），故
  `cpp_info.libs = ["ofx"]`；头文件安装于 `include/libofx/libofx.h`，
  故 includedirs 含 `include` 与 `include/libofx`。

## 上游测试盘点（申报表）

| 套件 | 数量 | 运行方式 | 本轮状态 |
|------|------|----------|----------|
| call-ofxdump（可执行冒烟） | 1 | `ctest` 之 `add_test(NAME call-ofxdump COMMAND ofxdump)` | build() 内 `ctest --output-on-failure` 实跑 |
| sample-file 用例（好样本 11 + 预期失败 9） | 20 | `ofxdump <sample>`，`OFX_DTD_PATH=dtd`，失败样本标 `WILL_FAIL` | 同上实跑 |
| ofx2qif / ofxconnect 测试 | 0 | 上游未注册 | 不适用 |
| make check / pytest / gtest | 0 | 上游 cmake 侧 TODO 明示 "wire up tests" 之外无其他框架 | 不适用 |

- 合计 ctest 条目：21（1 冒烟 + 20 样本）。9 个失败样本以 `WILL_FAIL true`
  注册，失败即符合预期，ctest 计为通过。
- 样本来源：`ofxdump/CMakeLists.txt` 之 `SAMPLE_OFX_FILENAMES` /
  `SAMPLE_OFX_FILENAMES_FAILING`，输入为 `doc/ofx_sample_files/*`。
- build() 内以 subprocess 跑 `ctest --output-on-failure` 并解析
  `N tests passed ... out of M`，输出 `HMBS_UPSTREAM_TEST_RESULT` 机器证据；
  结果同时落盘 `upstream_res/upstream_test_result.json` 并随包发布到
  `res/`，test_package 在缓存命中轮重放该标记。

## test_package 设计

- test_libofx.cpp（单一二进制，双套件）：
  - 套件 1 context（4 项）：版本宏 0.10.9 校验 +
    `libofx_get_file_format_from_str("OFX") == OFX` + description 非空 +
    `libofx_get_new_context / set_dtd_dir / free_context` 生命周期。
  - 套件 2 requests（3 项）：`libofx_request_accountinfo` 非空且含 OFX 标记 +
    `libofx_request_statement` 非空且含 OFX 标记（附带 minimal
    OfxFiLogin/OfxAccountData 结构体实参）。
  - 两个 sentinel（`test_libofx_context: all 4 checks passed` /
    `test_libofx_requests: all 3 checks passed`）分别作为 discovered=2 的
    两条用例判定。
- 第 3 条用例：运行包内 `ofxdump`（无参，上游 call-ofxdump 同款），要求
  退出码 0，覆盖 CLI 工具执行路径。
- 直接编译模式（libmustach-core validated pattern）：用 conan conf 编译器
  直调 `cc test_libofx.cpp -I... -L... -lofx -losp`，避开 CMakeToolchain
  在沙箱内 pin 绝对 clang 路径导致的 "compiler identification is unknown"。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ofxconnect 依赖 libxml++-2.6 不可用 | 上游 README：vcpkg 仅供 ABI 5.0，无 workaround | `ENABLE_OFXCONNECT=OFF`，PR 补充说明如实声明 |
| 2 | 库名易误判为 `libofx` | 上游 PREFIX 为空，实际链接旗 `-lofx` | `cpp_info.libs = ["ofx"]`，以 libofx.pc.in 为据 |
| 3 | OpenSP 头/库路径不固定 | FindOpenSP 先走 pkg-config，缺失则回退系统路径 | generate() 显式写缓存变量 + PkgConfigDeps 双保险 |
| 4 | 真机 Generate 失败 `OpenSP::OpenSP target not found` + `CURL::libcurl target not found` | ① `_opensp_dirs()` 只查三处固定头目录，真机 opensp 包头文件不在其中时 `OpenSP_INCLUDE_DIR` 为空，内建 FindOpenSP 建不出目标（conan 的 `opensp::opensp` 与上游要的 `OpenSP::OpenSP` 名字不同，接不上）；② `tc.variables["ENABLE_OFXCONNECT"]=False` 未能传到 configure（ofxconnect 子目录仍被添加），且 source() 从未打补丁 | 换路线：`_opensp_dirs()` 加全包递归回退搜索并双通道（cache+普通变量）写入 `OpenSP_INCLUDE_DIR/LIBRARY`；`ENABLE_*` 改用 cache 字符串 `"OFF"/"ON"`；CMakeDeps 增设 `opensp→OpenSP/OpenSP::OpenSP` 备用通道；source() 内以单行精确改写把上游 `ENABLE_OFXCONNECT` 默认值改 OFF（静态 patch 因上游行号漂移打不上，已删除改用程序改写，缺失时 loud fail） |
| 5 | 真机编译 `fatal error: 'ParserEventGeneratorKit.h' file not found`（messages.cpp:21 `#include "..."` 裸引号） | 目标 `OpenSP::OpenSP` 已存在（configure 通过），但其 include 只有 `<pkg>/include`；上游裸引号 include 需要 OpenSP 子目录本身在路径上（系统 FindOpenSP 返回的是带后缀的目录） | 双保险：① generate() 内把实测头目录追加进 opensp 的 `cpp_info.includedirs`（config 模式生效）；② `_scrub_toolchain` 幂等地向 conan_toolchain.cmake 追加 `include_directories(<头目录>)`（模块/配置任一模式都生效，generate 与 build 双调用点） |

## 验证结果

- 编译状态：待真机预检回填
- 上游测试用例通过率：待真机预检回填（ctest 21 项，build() 内实跑）
- 新增测试用例通过率：待真机预检回填（test_package 3 用例）

```bash
# 真机预检（hmbs 后台执行，待回填）
# conan create archives/l/libofx/0.10.9 -pr:h=ci/conan/profiles/ohos-aarch64 ...
```
