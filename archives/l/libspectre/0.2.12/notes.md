# libspectre 0.2.12 HarmonyOS PC 适配笔记

## 上游与依赖

- 上游仓库：`https://gitlab.freedesktop.org/libspectre/libspectre`
- 上游标签：`0.2.12`，提交 `44ba3f8291e5640045d501f130f8a4521fc407b3`
- 发行归档：`https://libspectre.freedesktop.org/releases/libspectre-0.2.12.tar.gz`
- SHA-256：`55a7517cd3572bd2565df0cf450944a04d5273b279ebb369a895391957f0f960`
- 编译依赖：`ghostscript/10.07.1.1`，产出 `libgs.so` 与 `include/ghostscript/iapi.h`。依赖 PR [#14671](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14671)，任务 #14845。该版本尚未进入制品仓。
- 关联 OHPCD 任务：#13639；知识库议题：[#3570](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3570)；适配 PR：[#13738](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13738)。

## 适配内容

- 使用 Conan Autotools 工具链生成交叉编译参数，并将 `compiler`、`build_type` 列为配方设置。
- 依赖 Ghostscript 共享库包，向 configure 的 `AC_CHECK_LIB(gs, ...)` 探测传递 `LIBS=-lgs`，并通过 Conan 元数据传播 `-lgs`、头文件和库目录。
- 显式传入 `--build=aarch64-unknown-linux-musl`，避免上游旧版 `config.guess` 在 HarmonyOS `/bin/sh` 下解析失败；上游 `config.sub` 已验证接受该三元组。
- 关闭上游可选 Cairo 测试构建；采用消费者测试覆盖安装头文件、链接、文档元数据和 Ghostscript 实际渲染。

## 测试说明

上游发行包提供 `spectre-test`、`parser-test`、`fuzz-test` 三个测试程序，但没有将它们登记为 `make check` 测试目标；`spectre-test` 另需 Cairo 测试依赖。test_package 以真实 PostScript 单页文档在 HarmonyOS PC 消费安装后的库，核对文档状态、页数、页面尺寸和渲染输出。

PR/CI 结果以最新提交对应的机器人状态为准，见 PR 正文与机器人评论。

## CI 记录

- PR #13738 首头 CI #64384 在 L0 门禁因 `test_package/conanfile.py` 的 `test()` 没有显式 `self.run()` 被拦截；已在后续提交中改为直接运行 `libspectre_consumer`。
- 修复头 CI #64404 在 `ci/conan/build_and_test.sh` 的 G0 阶段因 worker 资源不足报 `resource temporarily unavailable: wc` 并以 127 退出；日志未到包的 L0 检查、编译或 test_package。该失败没有提供新的配方问题证据，后续新头仅用于重新调度 CI。
- 重排头 CI #64419 进入 Conan 构建后发现，追加的 HarmonyOS 分支仍会在目标机旧版 `config.guess` 后续 `case` 下触发语法错误。现改为通过 `AutotoolsToolchain` 显式传入 `--build=aarch64-unknown-linux-musl`，不再补丁上游脚本；本地 `config.sub` 验证接受此三元组，后续需由 HarmonyOS CI 验证 configure 完整链路。
- 修正头 CI #64426 在 worker-prep、git-clone 与 cleanup 阶段均因 `resource temporarily unavailable` 退出 127；未执行 Git clone、L0 或包构建。该基础设施失败不代表 libspectre 配方失败，后续新头重新调度以取得有效构建结果。
- 显式 build 三元组头 CI #64439 在 worker-prep、git-clone 与 cleanup 阶段因 `resource temporarily unavailable` 退出 127，未到 L0 或 Conan 构建。继续跟踪有效的包构建结果。

## 2026-10-02 — Septest VERDICT #192419776 修正

- CI #64480 的评论日志显示，预下载辅助步骤因 worker 缺少下载命令连续失败，但该步骤明确回退给 Conan；随后 Conan `source()` 成功下载官方归档并校验 SHA-256。该警告并非终止原因。
- 实际终止发生在 Autotools configure 的 C 编译器初始链接检查（`C compiler cannot create executables`）。当前日志未提供 `config.log` 的底层 linker 诊断；配方原先把 `LIBS=-lgs` 全局传给 configure，故移除这项全局注入，让上游 `AC_CHECK_LIB(gs, ...)` 对 libgs 做定向检测。
- 为避免预下载器从 `conandata.yml` 扫描 URL 后调用外部下载程序，改为在 `source()` 中用 Conan 内置 `get(url, sha256, strip_root=True)` 获取同一官方归档，并删除不再使用的 `conandata.yml`；版本、来源 URL 与 SHA-256 未变。
- PR 正文将编译状态明确记为 CI #64480 未通过、消费者测试未执行（0/4），不把基础设施警告写作包编译成功。待新头 CI 结果覆盖后再更新为最终实测状态。

- 当前头 `699a7eaf` 的 CI #66829 在 `worker-prep`、`git-clone`、`cleanup` 的 SSH bridge 连接均被拒绝；没有 checkout PR、L0 或 Conan 运行记录，故不作为新配方构建结果。PR 正文的状态字段改为 ASCII 冒号并明确记录未完成，消费者测试计数保持 0/4（未执行）。
- 对 e5c2676e 的一次 rebuild 是 CI #66838；与 #66829 一样，worker-prep/git-clone/cleanup 的 SSH bridge 均返回连接被拒绝，未 clone、未 L0、未 Conan。PR 正文与记录更新为当前头事实；未将其误记为源码下载超时或配方失败。

## 2026-10-03 — HarmonyOS 设备真实构建复核

- 首次 `conan create` 在 `export_sources()` 因配方已无 `conandata.yml`、却仍调用 `export_conandata_patches()` 失败；已删除失效补丁入口，并同步执行上游 `make check`。该次退出码 1，属于配方问题。
- 修复后重新执行，源码下载和 Autotools configure 均开始；`aarch64-unknown-linux-musl` 被接受，失败点为 `checking for gsapi_new_instance in -lgs... no` / `configure: error: You need libgs in order to compile libspectre`。设备私有 Conan 缓存内 `ghostscript/10.07.1` 实际仅含 `bin/gs` 等命令与资源，没有 `lib/libgs*` 或 `include/` 开发头文件。Conan `AutotoolsDeps` 生成的搜索路径也指向这两个缺失目录，故该问题不是 CI 桥接故障。
- 当前可确认上游自动化用例数为 0：0.2.12 的 `Makefile.am` 只在启用可选测试时进入 `test/`，`test/Makefile.am` 声明三个 `noinst_PROGRAMS`，没有 `TESTS` 变量。设备构建未通过 configure，未到 `make check` 或 test_package；正文如实记录上游 0/0、HarmonyOS 消费者 0/4。
- 消费者 C 程序现在逐项打印四条 `PASS 1/4`…`PASS 4/4`，最终打印 `HARMONYOS_TESTS=N/4`，但因依赖缺开发库，当前没有伪报任何通过结果。

- 上游 Ghostscript `10.07.1` 的旧制品只含 `gs` 命令与资源。新依赖配方版本 `10.07.1.1` 针对同一官方源码运行上游 `make so` / `make soinstall`，并安装 `psi/iapi.h` 为 `include/ghostscript/iapi.h`；依赖任务 #14845，依赖 PR #14671。

## 2026-10-04 — 使用 ghostscript/10.07.1.1 的真机全链

- 隔离 `CONAN_HOME=$HOME/work/psj/ch-gs14845`（与 ghostscript 10.07.1.1 同缓存，包 `01d92cf349a0dd98ff915f4bd99a04430171517f` 已在缓存）。`conan create archives/l/libspectre/0.2.12 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` 退出码 0。日志：`$HOME/work/psj/ls13639/create.log`。
- configure：`checking whether we are cross compiling... no`；`checking for gsapi_new_instance in -lgs... yes`；`checking for libgs >= 9.53.0... yes`。
- 两处配方修正：构建环境补上 ghostscript 的 `lib` 目录，否则 AutotoolsDeps 注入的 `-lgs` 让「能否运行编译结果」测试因找不到 soname 失败；`configure` 临时目录 `umask 077` 改为 `022`，否则 HMDFS 上 `config.status` 写 `subs1.awk` 报 Permission denied；`Makefile.in` 增加 `-I$(top_srcdir)`，否则离树编译找不到 `<libspectre/spectre-macros.h>`。
- 上游 `make check -j1` 已执行。输出 `Nothing to be done for 'check'`。`--disable-test` 未进入 `test/`。发行包没有 `TESTS` 登记，计数 0/0。三个 `noinst_PROGRAMS` 不计入。
- 消费者 4/4：`PASS 1/4` 文档载入，`PASS 2/4` 一页，`PASS 3/4` 页面尺寸为正，`PASS 4/4` Ghostscript 渲染像素缓冲，`HARMONYOS_TESTS=4/4`。
- `make install` 与 test_package 的 gmake 打印 `jobserver mkfifo ... Operation not permitted`。安装和链接仍完成，测试通过。这是已有的 FIFO 限制，不新开知识条目。
- 制品仓尚无 `ghostscript/10.07.1.1`。合入顺序必须是先合入并发布 #14671，再合入本 PR。在此之前 CI 的 L0i 失败是预期结果。真机通过不写成 CI 通过。ghostscript 包契约：`cpp_info.libs` 含 `gs`，并安装 `include/ghostscript/iapi.h`。
