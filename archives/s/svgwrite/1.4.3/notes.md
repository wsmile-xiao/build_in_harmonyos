# svgwrite 1.4.3 适配笔记

## 当前状态

- 状态: H1 v11 已验证 Conan G1/G2、pytest 478/478（1.79s）和消费者 4/4；W3 本地 CI setup/build 均 rc0、pytest 478/478（1.72s）、消费者 4/4。finish 实际退出码 rc1（失败步骤 step5b、step8），不得视为收尾通过。Conan Verify 的 G4 未定位 package ID，L2/L4/L5 因无 cache 路径跳过；后续官方 Worker CI #61615 在缺 pytest 的旧配方输入上失败（见后续记录）。结果对应冻结候选 ZIP SHA-256 `1cb134ec98ae371ce758a95fede027ccbacaf4666ea11c5e59263354b9bbe7d2`，原始回包 SHA-256 `e1e9bd141f61326e3253adc6c5d0ef5d3fe9b43555823a4f9e3ae09ebbc179c7`。
- 上游来源: PyPI `svgwrite-1.4.3.zip`，SHA-256 `a8fbdfd4443302a6619a7f76bc937fc683daf2628d9b737c891ec08b8ce524c3`。
- 构建方式: 纯 Python 文件由 Conan 打包，构建阶段用标准库 compileall 检查包和测试源码语法；完整上游 pytest 在有测试工具的 H1/W3 环境单独运行，包消费者检查 SVG 生成和解析。
- 许可证: 固定 sdist 中的 `LICENSE.TXT`，MIT。

## 源码与测试修改

- `0001-svgwrite-data-svgparser.py.patch` 将路径数据正则中只用于分组的捕获组改为非捕获组；`0002-tests-test_pathdataparser.py.patch` 增加长有效路径及短非法尾部回归；`0003-tests-test_style.py.patch` 将联网 Google Fonts 用例改用固定 CSS/字体字节，仍检查嵌入结果。15,470 字符上游样本的本机 Python 3.11 中位数由 37.574 ms 降至约 2 ms。长有效路径后接非法尾部仍可能严重回溯，不能声称解决最坏输入性能。
- 三份补丁均在固定 sdist SHA-256 `a8fbdfd4…e524c3` 的 orig/work 树上由官方 `python3 scripts/ohc-run.py refresh-patch --auto svgwrite 1.4.3 --project-dir <隔离项目>` 真实生成。官方工具读取 CRLF 时把补丁行归一化为 LF，首次原样 dry-run 因行尾不一致未生成；随后对 orig/work 中同三份 `.py` 一致归一化为 LF，未改代码语义，WSL 原版脚本产生三份补丁并逐份 dry-run 通过（orig hash `d4cc05e57e4481d0`，work hash `e0b558a7839d8905`）。v7 H1 证实生成补丁无法直接严格应用于原始 CRLF 文件；v8 配方从固定 sdist 解包后先对这三份文件作 CRLF→LF 归一化，再应用未改动的官方补丁。本机按同一顺序严格应用后，三文件与 v6 受测源码的 LF 内容逐字节相同。原始命令/输出及归一化哈希留在本地隔离证据，不进入候选提交。
- 原始未修改上游完整 pytest: Windows 476 通过、1 失败，失败为 Google Fonts 请求；原始日志留在本地，不进入 PR。
- v6 两份旧补丁后完整 Windows pytest: 478/478（原 477 项加一项回归）；v8 在配方的行尾归一化后严格应用三份官方补丁，本机完整 pytest **478 passed in 1.53s**。此结果不是 H1 证据。
- 旧 v5 H1 finish 原始结果：ConanVerifier 完整 pytest 476 通过、1 失败，性能用例 0.1071538925 s；W3 同项 0.108643055 s，setup rc0、build_and_test rc1，消费者未运行、finish rc1。原始失败保留。
- v6 H1 原始归档 SHA-256 `be54719050525df894788a9005386c238759324f4b46a755c7b3075df7cd2eba`：G1/G2 通过、完整 pytest 478/478、正式包消费者 4/4、W3 setup/build 双 rc0；整体 finish rc1，finalize 缺 release/debug 包及 staging/test-report，summary 还报类型错误。此结果绑定 v6 差异，不能冒称 v7、完整 finish 或官方 CI 通过。
- v7 H1 原始预检归档 SHA-256 `44f26a22a78c1b05844e8f3cf8a6c93213ec1ebc99e0edbb42b47e5b7d7bbda4`：原始 `svgparser.py` 全 132 行 CRLF，第一份官方补丁全 27 行 LF；严格 `git apply --check` 失败于第 77 行。runner/preflight rc2，finish、Conan、pytest、W3 均未运行。

## Official Worker CI follow-up

- 官方 PR CI #61615 / Worker CI-030 在 Conan `build()` 失败：`/data/service/hnp/bin/python3 -m pytest tests -q` 报 `No module named pytest`。L0/KC 已通过、源码下载并应用三份补丁；这是干净 Worker 缺少测试运行器，不是源码补丁或编译器错误。原始 bot comment 为 191704983。
- 最小候选修正：Conan `build()` 改用标准库 `compileall -q -f svgwrite tests`；`test_package/MANIFEST.yml` 标记 `upstream_test_in_build: false`，保留 pytest 命令/测试清单，并准确说明 pytest 仅在 H1/W3 提供了测试运行器的环境执行。`test_package` 的真实包消费者检查保持原样。
- 2026-09-26 记录：拟议修改当时尚未应用到 MR 或提交；官方 Worker CI/OHOS H1 尚未验证该新输入。旧 H1/W3 pytest 结果绑定旧配方输入，不能代替新输入验证。

## 运行与回收

- H1 v11 已按冻结 v8 候选执行一次 Conan 复验与 W3 本地 CI；详细阶段结果及边界见上方状态和本地审核报告。不得把 finish rc1 改写为成功，也不得把 W3 本地 CI 记作官方 CI。
- 需保留旧 v5 失败、v6 H1 通过阶段与 finish rc1、v7 预检失败及后续 H1 原始日志；不能据阶段通过推定完整 finish 或官方 CI 通过。
- 平台任务 #10922 标为 `lang=cpp`，源码实际为 Python；人工路径受理与计分仍待确认。

### 对话 #1：本地准备

从固定 sdist 核对单一根目录、三个 Python 包目录和 MIT 许可证。依官方 `refresh-patch --auto` 生成并核验测试补丁，准备 Conan 配方、消费者、归档元数据和 H1 冻结输入。本记录未宣称任何目标机验证通过。
