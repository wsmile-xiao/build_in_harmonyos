# tshark 4.6.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang/clang++
- 状态: {published|built|failed}

## R51 上游测试清点（申报表）

**测试框架**: pytest（Python）+ pytest-xdist 并行；**非 ctest**（全树无 `add_test`，`test/` 下无 CMakeLists.txt）。
`pytest.ini`: `testpaths=test`、`python_files=suite_*.py group_*.py`、`addopts=-ra -nauto`。

| 项 | 数量/说明 |
|---|---|
| 顶层套件 `test/suite_*.py`（18 个）静态 `def test_` | **460** |
| `test/suite_dfilter/`（group_*.py 为 pytest 入口）静态 `def test_` | **≈496**（精确值以 `pytest --collect-only` 为准） |
| `test/suite_dissectors/`（4 个 group_*.py）静态 `def test_` | **23**：asterix 11 / mysql 6 / netperfmeter 5 / zabbix 1（zabbix 参数化后 7 个子用例）；asterix category 034 的 2 个函数被上游以 `_disabled_TestCategory034` 类名禁用（pytest 不收集，与上游行为一致） |
| C 辅助测试程序（`test-programs` 目标） | 10 个：exntest / fifo_string_cache_test / oids_test / reassemble_test / tvbtest / wmem_test / wscbor_test / wscbor_enc_test / test_epan / test_wsutil（+ dftest，BUILD_dftest 选项） |
| 抓包夹具 `test/captures/` | **183** 个 .pcap/.pcapng |
| Lua 解码头夹具 `test/lua/` | *.lua（wslua 套件用） |

**运行方式**（对齐 CI `.github/workflows/ubuntu.yml`）：`ninja test-programs` → `pip install pytest pytest-xdist` → `pytest`（自 build 目录；或 `cmake --build . --target test`，CMake 包装 `${Python3_EXECUTABLE} -m pytest`）。

**本机测试依赖**：python3 3.12.9 ✓；pytest 待装（pip 社区源）；**perl 不需要**——证据：`test/` 下 0 个 `.pl` 文件，全树仅 2 处 "perl" 文本命中均为单词 "properly" 的子串误报，pytest 套件无 perl 调用。

**可运行性预判**（R51 步骤 2 将在真机/CI 逐条回填 N/N′/通过率）：dfilter / dissection / decryption / clopts / outputformats / fileformats / follow* / text2pcap / io / mergecap / sharkd / wslua / release / extcaps 依赖构建产物，预计可运行；**capture 族（28 例）需 raw socket 实时抓包，OHOS/CI 受限环境大概率不可运行，届时逐条列具体技术原因**。

**实测回填（2026-10-02，OHOS aarch64 真机）**：suite_dissectors 23 个静态 test 函数中 21 个可执行（2 个 category 034 函数上游禁用：源 group_asterix.py:779 `_disabled_TestCategory034`），真机实测**全部通过**（真机 python3 3.12.9 + pip 社区源 pytest 9.1.1 收集 27 项，27/27 passed；证据日志 scratch pytest-run.log）。可执行性要点：asterix 11 例走 hex byte bundle → text2pcap → tshark 生成链（本配方不建 text2pcap——它链接 libwireshark；以 Python 等效桩生成 UDP/IPv4/Ethernet 封装 pcap，断言仅查协议层、不依赖封装头细节）；mysql 6 / netperfmeter 5 / zabbix 1×7 直接用上游 test/captures/ 的 .pcapng.gz 夹具（纯文件解析，无 raw socket）。已移植为 CI 可执行的 L2 bash 快照测试（`test_package/dissectors/`：27 例 = 同输入 capture + 同 tshark 命令行 + 输出比对；TZ=UTC + PDML 头运行值归一化；bash-only 无 python/pytest 依赖），本地实测 27/27 通过，由 conanfile test() 与 L1 一并执行。**测试数据格式（2026-10-02 更新）**：27 个 capture 以 `.b64`（base64）形式入仓，runner.sh 运行期 `base64 -d` 解码到 scratch 目录后消费（解码后 sha256 与原始字节一致）。原因：GitCode PR .diff 端点不带 `--binary` payload（构建 #67201 checkout-pr 实测：996KB diff 中 GIT binary patch 段=0、`Binary files ... differ`=27），CI `git apply` 无法物化二进制文件（逐文件报 `missing binary patch data`；该错误与 main 冲突无关，日志 HINT 有误导）——仓库先例 packetq/sngrep `.pcap.b64`。此前"不转 .b64"的决定基于 junk_check 分析（JC2/JC3 不拦 .pcap/.gz），未覆盖 .diff 机制约束，现予推翻。详见知识草稿 `DRAFT-tshark-4.6.7-gitcode-pr-diff-no-binary-b64` 与 Issue #3688。

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-28 19:38
**最终状态**: built
