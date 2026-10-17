# socksio 1.0.0 适配记录（候选）

2026-09-25。源码固定为 PyPI `socksio-1.0.0.tar.gz`，SHA-256
`f88beb3da5b5c38b9890469de67d0cb0f9d494b78b106ca1845f96c10b91c4ac`。
源码包含 MIT `LICENSE`、七个 Python 模块、`py.typed` 和完整 `tests/`。
目标为 OpenHarmony PC aarch64，包只含 Python 源码、类型标记和许可证，无原生编译或运行依赖。

配方从带 SHA-256 的 PyPI URL 取源码；隔离 H1 验证可用 `SOCKSIO_SOURCE_ARCHIVE`
指定同哈希的本地 sdist，源码函数会重新计算 SHA-256 后解包，正式元数据仍保留 PyPI URL。
备选 B 的 `build()` 仅用目标机 Python 标准库执行 `python3 -m compileall -q socksio`
核七个分发模块的语法；这不是上游功能测试。生成的 `.pyc` 留在源码目录，
`package()` 仅复制 `*.py`、`py.typed` 和 MIT 许可证，不把 `.pyc` 纳入包。
固定 sdist 的上游 99 项仍须单独在 H1 执行原命令
`python3 -m pytest tests -q -o addopts=`，并以原始日志证明。
`-o addopts=` 仅关闭 sdist `pytest.ini` 默认要求的可选覆盖率插件参数；没有筛除测试。
Conan/W3 的 `test_package` 另跑五组消费者，验证包来源及 SOCKS4/SOCKS4A/SOCKS5 协议行为，
不可把五组视为上游 99 项。

Windows Python 3.11 上游 99/99、固定 sdist 模拟包消费者 5/5 已通过。
二级管家报告 H1-006 用旧配方在 Conan create 与完整 W3 中均对同固定源码
运行上游 99/99（私有 RUNROOT `/data/storage/el2/base/files/ohpc-socksio-006.CAHpCn`）；
这对备选 B 是此前 H1 真机上游证据，**不代表备选 B 的 `build()` 跑过 99 项**。
006 原始回收包 SHA-256 为 `d5727c9a32c2ce733b2d4a76b7aba11466e2d824ecbed602c2e1556ab74ff4b4`；
其中 W3 原始日志 SHA-256 为 `bc8c7324ad1056794b6468a5fb37762f46fc7813d2dfa9587c2cc47066b720331`，
旧配方消费者结果文件 SHA-256 为 `202d950f72392020ca5dae647c1e8965ba9b908cbe5914406a1d0d3b8b6ec5aa`（5/5）。
006 的 Conan create、W3 setup/build 和 CI exit 均为 0；其原始 tar 可供逐项复核。
备选 B 已在 H1-007 真机运行 Conan create 与完整 W3：两次 `compileall`、两次真实包消费者 5/5，
setup/build 与 CI exit 均为 0；原始 tar SHA-256 为
`0a4f7fc97aa2ff064d30acdeaec57c35ac945233fd97965fd75a9fd7a6c11c94`，
W3 原始日志 SHA-256 为 `a6e25a41eaf6c9e688535646045a97cdf522bab4bae9a7f2122a04df3c7394f7`。
007 未重跑上游 99 项，不能把 006 的独立上游结果称为 007 Conan build 测试。
007 G1 rc1、finish rc1、单独 finalize rc2；工具途中把版本状态写为 built 不代表总门禁通过。
本最终候选状态仍为 pending，独立 W4、官方 CI 和 PR 均未完成。
H1-008 已另行生成并回收真 release tar；这不改变 007 的 G1/finish/finalize 失败。
平台任务 #10785 公开标签 `cpp` 与实际 Python 源码不符；按正常人工路径试验，
不更改任务标签或提交错误的 AI Worker 终态。正式受理及计分仍待官方核实。

### 对话 #1：本地候选准备

核对固定 PyPI sdist 的 SHA-256、MIT `LICENSE`、源码与上游测试目录；
在 Windows Python 3.11 上运行上游 pytest 99/99，并用固定源码模拟包运行消费者 5/5。
准备 Conan 配方、两级 manifest、H1 冻结输入和本地单软件候选。
本条只记录本机准备；尚无 H1 Conan、完整 W3、独立 W4 或官方 CI 结果。

### 对话 #2：clean CI 测试依赖备选（本地草案）

H1 原环境无 pytest，现行 005 的 `build()` 若在相同无 pytest 的干净 CI 环境执行，
会在 `package()` 和五组 `test_package` 前报错。备选 B 保留 `build()` 的真实语法检查，
上游 pytest 另以 H1-006 同固定源码的原始 99/99 作为 R51 证据，并将 `MANIFEST.yml` 的
`upstream_test_in_build` 设为 `false`；官方 W3 的 L1a/L1e 仍需真实运行消费者及反向验证。
此处记录的是 H1-007 运行前的本地备选；005 固定候选或 ZIP 未修改。G1 对 `export_sources`、
`apply_conandata_patches` 的通用静态要求与本纯 Python 无补丁配方冲突仍未解决。

### 对话 #3：H1-007 实测与门禁回收

2026-09-25，H1 私有根 `/data/storage/el2/base/files/ohpc-socksio-007.mfEBEk`。
原始回收 tar SHA-256 `0a4f7fc97aa2ff064d30acdeaec57c35ac945233fd97965fd75a9fd7a6c11c94`。
Conan create rc0，`python3 -m compileall -q socksio` 真执行，真实包消费者 5/5。
W3 `setup.sh`/`build_and_test.sh` 均 rc0，JC `prdiff (9)`/pass，第二次 compileall 和消费者 5/5；
`.ci-result.json` exit0，W3 日志 SHA-256
`a6e25a41eaf6c9e688535646045a97cdf522bab4bae9a7f2122a04df3c7394f7`。
本轮没有注入 pytest ZIP，也没有跑上游 99 项；该项仅由同源码 H1-006 提供历史独立证据。
conan-verify G1 rc1，报告缺 `export_sources()` 和补丁应用调用；本库没有真实补丁，
因此未为静态文本检查添加空壳补丁。finish 总 rc1、最终状态 failed；单独 finalize rc2 缺 release tar。
工具曾把版本 manifest 写为 built，但不能据此宣称正式门禁通过。
真 Conan 包由消费者报告绑定到原私有 cache；随后 H1-008 在同一包前缀完成独立 release 打包续测。

### 对话 #4：H1-008 真包独立打包续测

2026-09-25，在原 H1-007 私有根核真 Conan 包 11 个文件逐 SHA，并运行官方
`verify-build` 与 `ohc.package_builder.package_cli`，runner/两入口退出码均为 0；
没有重跑 Conan create 或 W3。原始回收包 SHA-256
`b05cb5f9450f62c1aa1805aa1aa7c8e46af8196ab42e174c0fabca864f0cd675`。
其中真 release tar 为 39,452 B，SHA-256
`591d255db8727624a6c87db9a303d69f2b510fb05c3c31530f1e3ff895b7de44`；
本机独立流式核九个普通文件逐 SHA 与真 Conan 包一致，无 ELF/链接。
但 008 release tar 内文件 mode `0600`、目录 mode `0700`、所有者 UID/GID `20020084`；
跨 UID 安装读取存在实际阻塞。原 Conan 真包对应文件 mode `0644`、目录 `0775`。
008 tar 仅作失败证据，须在隔离目录用适当 umask 经官方打包入口重试并核权限。
`verify-build` 报告 Verdict PASS，G2 为零通过、一警告（包无 `bin/`，纯 Python 无二进制入口）；
它不是 Conan G1 的通过证据。007 的 G1 rc1、finish rc1、finalize rc2 和 W3 原件前后未改，
最终候选仍为 pending，独立 W4 与正式 PR CI 尚无通过结果。
