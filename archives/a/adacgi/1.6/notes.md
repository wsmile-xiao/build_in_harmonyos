# adacgi 1.6 HarmonyOS adaptation notes

Issue: pending (待补)

## 目标与结论

adacgi 1.6 是 David A. Wheeler 开发的 Ada 95 CGI 接口库，包含 `CGI` 与
`Ustrings` 两个纯 Ada 源码单元，无 C/C++ 依赖。适配方式为源码分发：打包
未修改的上游源单元，下游用 `gcc-ada/9.5.0`（GNAT）现场编译。

## 上游信息

- 上游：David A. Wheeler，AdaCGI（http://www.dwheeler.com/adacgi）
- 源码归档（Debian 权威镜像）：
  `https://deb.debian.org/debian/pool/main/a/adacgi/adacgi_1.6.orig.tar.gz`
- SHA256：`6a417f4936a362c1d3d85b8331c26be4ef381ce152cf03c39ac1d5c86fdb884c`
- 许可证：主库 LGPL-2.1-or-later（`lesser.txt` + `cgi.ads` 声明）；`Ustrings` 公有领域
- 库单元：`cgi.ads`/`cgi.adb`、`ustrings.ads`/`ustrings.adb`（未修改，仅去尾随空行等非语义差异）

## 依赖（W0）

- 运行时依赖：无
- 构建依赖（tool_requires）：`gcc-ada/9.5.0`（GNAT 编译器，提供
  `gnatmake`/`gnatbind`/`gnatlink`/`gnatchop`）
- 结论：`gcc-ada/9.5.0` 已合并 main（PR #6116，issue #2281），CI #42755
  完整上游证据与 CI #42923 最新 merge-gate 均通过，无实现阻塞。其 manifest
  `status` 仍为 `built`（非 `published`），发布到制品仓的状态需在真机/CI 环境
  用 `conan download gcc-ada/9.5.0 -r=ohpcd --only-recipe` 确认（R35/R36）。
  本机无 conan，无法完成该项验证，故本轮只做本机前置准备。

## 上游自带测试的取舍

上游归档自带 `test_get.adb`、`test_cookie.adb`、`test_encode.adb`、
`test_send.adb`、`demo.adb`、`minimal.adb`、`search.adb` 等演示/测试程序。
它们面向交互式 CGI 环境（依赖 HTTP 服务器或手动输入），不适合作为 Conan
`test_package` 的确定性断言。因此 `test_package` 采用复用自 gcc-ada 集成的
确定性九断言消费者测试（`test_adacgi.adb` + `verify_adacgi.py`），无外网、
无交互依赖，可稳定失败即退出非零。

## 复用说明

`test_package` 的消费者用例与验证脚本复用自 `gcc-ada/9.5.0` 配方中对
AdaCGI 1.6 的集成验证资产（`test_adacgi.adb` 九断言 + `verify_adacgi.py`），
语义未变。该资产原先作为 gcc-ada 的集成测试存在；本次将其作为 adacgi 独立
包的下游消费测试，符合 JC6 单软件原子性与 R36 依赖发布顺序。

## 真机 shadow CI 修复记录

真机隔离 job 首轮 `conan create` 暴露四个问题，已全部在配方内修复：

1. **`package_type="library"` 缺 shared 选项**：Conan 2.x 要求 library 类型
   声明 `shared`。AdaCGI 是纯源码分发，改用 `header-library`（无需 shared）。
2. **`as` 汇编器 Permission denied**：GNAT 驱动用 `execvp("as")` 在 PATH 找
   汇编器，`/usr/bin/as` 受 SELinux 保护不可用，而 GNU binutils 在
   `/data/service/hnp/bin`。配方 `generate()` 将 `/data/service/hnp/bin` 前置到
   PATH（`adacgi_binutils_env`）。
3. **test_package 找不到 `system.ads`**：gcc-ada 是 `tool_requires`（build
   context），其 `ADA_INCLUDE_PATH` 在 `conanbuild`；test_package 的 build()
   改用 `conanbuild`（而非 conanrun）。
4. **签名工具缺失**：`binary-sign-tool`/`llvm-objcopy`/`llvm-readelf` 不在
   隔离 PATH，`_sign_program` 增加 `/data/service/hnp/bin/` 显式 fallback。

## 验证状态

- 本机前置：Python/YAML 语法、源码 SHA256 复核、目录边界检查通过。
- 真机 shadow CI：**通过**（隔离 job `adacgi-1.6-shadow-20260917-092524`）
  - L0=pass，L1=pass（test_package 执行），L2=skip（无 bin/），
    L4=pass（无补丁），L5=warn（header-library 无 .a/.so 产物，正常）
  - `ADACGI_LINKAGE=pass assertions=9`
  - 依赖 `gcc-ada/9.5.0` 已发布（recipe `a418dfa7`，binary 53MB 下载成功）

## Resume commands

```sh
python3 scripts/ohc-run.py conan-verify adacgi 1.6
CI_PACKAGES="archives/a/adacgi/1.6" zsh ci/conan/build_and_test.sh
```

第二条命令仅能在持有全局设备锁时运行。真机隔离 job 复跑命令：

```sh
sh "$HOME/ohos-users/codex/adacgi-1.6-shadow-20260917-092524/run-conan-heavy.sh"
```

## 路径 B / B 类候选知识草稿

本库适配沉淀 2 对（4 文件）可复用知识草稿，位于 `knowledge/drafts/`，均保留
`draft: true`、不预占正式 E 编号、不声称已获 B 类认定；最终分类以维护者与评审为准：

1. `DRAFT-adacgi-ada-source-library-conan-pattern.{kv,md}`
   —— Ada 源码库在 HarmonyOS 的 Conan 适配模式（header-library + gcc-ada
   tool_requires + gnatmake 现场编译 + adainclude 暴露 + conanbuild 消费测试）。
   覆盖知识库此前空缺的 Ada 语言库配方契约。
2. `DRAFT-gnat-consumer-ohos-hnp-binutils-path.{kv,md}`
   —— GNAT 消费端需 GNU binutils 在 PATH（`/usr/bin/as` 受 SELinux 保护，
   `execvp("as")` Permission denied；`generate()` 前置 `/data/service/hnp/bin`）。

两条均与现有条目差异化：`DRAFT-gcc-ada-ohos-*` 覆盖工具链自身 bootstrap/链接，
`E012`/`E450` 覆盖 binutils 缺失与交叉工具链打包，本两条聚焦「下游 Ada 库消费」与
「SELinux 保护的 as + HNP binutils 前置」，不重复。
