# debianbuttons 2.3 — HarmonyOS PC 适配笔记

## 一、包性质（为什么"没有可编译的代码"）

debianbuttons 2.3（Debian「icedeb」/「Debian queries」）是 Damyan Ivanov 编写的
Firefox/Thunderbird webextension：根据剪贴板文本查询 Debian 相关网站
（packages.debian.org / tracker.debian.org / bugs.debian.org /
security-tracker / piuparts / lists.debian.org 等）。上游 orig 源码包共
**15 个文件**，全为 JS/CSS/HTML/JSON/资源：

| 类 | 文件 |
|---|---|
| 核心逻辑 | `icedeb.js`（popup，256 行）、`icedeb-content.js`（内容脚本） |
| UI | `icedeb.html`、`icedeb.css` |
| 元数据 | `manifest.json`（manifest_version 2，version 2.3） |
| 文档/打包 | README、Changes、TODO、Makefile（仅 `all`：zip 打包 icedeb.xpi） |
| 资源 | `icons/*.svg`、`res/icon.xcf` |

全树**零 C/C++ 源文件、零可执行程序、零测试框架**；上游唯一"构建"是
Makefile 的 `all` 目标把 12 个文件 zip 成 `icedeb.xpi`（分发产物）。

## 二、R47 语言预检判定（如实披露）

`lang-preflight` 实测：`detected_language=mixed`（manifest=顶层 Makefile、
build_system=make、source_stats=nodejs 2 文件占 100% → 边界规则「manifest
与统计矛盾判 mixed」），与任务默认语言 `cpp` 不匹配 → exit 2 → 按铁律 R47
终态 `env_unsupported`（平台转 **lang_hold 挂起等生态，非失败**），终态已
写盘 `$HOME/ohpcd-ai-worker-result.json`（draft=false，含 detected_language
与三项 evidence）。

**本 PR 的处置**：平台知识库扩展子流程 2.2 要求 PR 文件改动同时包含
`archives/`（适配代码）与 `knowledge/`（知识文档）。按同族先例
debian-pan (#9214) / debian-science (#9242) / debichem (#9205) /
debian-parl (#9217) 的 metadata/registry 数据包建模，本 PR 交付**真实的
webextension 产物**：

- `archives/d/debianbuttons/2.3/`：数据包配方（`package_type="unknown"`，
  零 Conan requires，不产 bin/ 与 ELF，不伪造编译）；`build()` 用 Python
  stdlib zipfile **逐项复刻上游 Makefile 的 `all`**（文件清单与上游
  `ALL_FILES` 完全一致），`package()` 装源码树 + 构建出的 `icedeb.xpi`
  （sha256 `2d2eb492…5986`，本机上游 Makefile 实测构建）；
- `test_package/test_debianbuttons.py`：30 项断言真实校验打包产物
  （布局/manifest 契约/引用闭包/xpi 归档逐条目字节一致/无 bin/无 ELF）；
  本机另有 node 版消费者套件 `test-icedeb-xpi-consumer.js` 15/15 双跑一致；
- `knowledge/drafts/E543/E544`：R47 判定模板 + 无测试上游测试补充与
  评审口径合规模板（两条草稿与本配方同 PR 提交验证）。

R47 判 lang_hold 与「交付真实数据包产物」不矛盾：**不做 C/C++ 空壳编译**
（R8/R34 禁止），交付的是可核验的扩展产物与校验证据。

## 三、建模决策（诚实、零伪造）

1. **单一 data package**：`package_type="unknown"`；`package()` 只装真实
   上游制品（源码树 + 构建的 icedeb.xpi），不制造假 `.so`/假 executable。
2. **零 Conan `requires`**：webextension 无库依赖；机械声明任何 requires
   都会造出虚假依赖图（R36 语义）。
3. **不产假 bin/**：`cpp_info.bindirs = []`，包内无 bin/、无 ELF
   （test_package 有显式诚实性断言），不触发 L0k/R38 commands.json。
4. **构建可复现**：`icedeb.xpi` 的 zip 条目与上游 Makefile `ALL_FILES`
   完全一致；归档 sha256 因 zip 内嵌 mtime 而随构建时间变化，故 test_package
   用**逐条目字节比对**证明构建未篡改源码（xpi 内 manifest.json/icedeb.js/
   icedeb-content.js/icedeb.html/icedeb.css == 打包源码）。

## 四、上游测试清点（R51，N=0 证据）

| 清点项 | 命令 | 结果 |
|---|---|---|
| 测试文件/目录 | `find . -iname '*test*'` | 0（无任何含 test 的文件/目录） |
| 测试框架 | manifest.json permissions 仅 activeTab/storage/clipboardRead | 无 Jest/Mocha 等 |
| 测试脚本 | `find . -name '*.test.js' -o -name '*.spec.js'` | 0 |
| Makefile 目标 | `grep -E '^(check\|test\|install):' Makefile` | 无（仅 `all`） |
| **合计** | — | **0（上游确无测试）** |

## 五、测试与通过率（实测回填）

| 测试集 | 对象 | 用例数 | 通过率 | 运行方式 |
|---|---|---|---|---|
| 源码级单元测试 | `icedeb.js`/`icedeb-content.js` 业务逻辑（trim/查询词解析/URL 构造/消息链/剪贴板/设置） | 23 | 23/23（100%） | node v24.13.0 `--jitless`（本机实测） |
| 产物级消费者测试（鸿蒙特有） | 构建产物 `icedeb.xpi` 装载验证（C1–C15：归档完整性/无路径穿越/manifest 契约/引用闭包/端到端查询链路/内容脚本跳转/连续装载） | 15 | 15/15（100%） | node `--jitless`（本机，基线产物 + 重建产物两轮） |
| test_package 产物校验 | 打包目录 + manifest 契约 + xpi 归档逐条目比对 + 无 bin/ELF | 30 | 30/30（100%） | `python3 test_debianbuttons.py`（conan create 内 self.run 实测） |

三集互不重复；汇总口径见 `reports/test-report.md` 与 PR 描述。

## 六、已知限制 / TODO

- 本包交付扩展**源码 + 构建产物**及其校验证据；webextension 在 OHOS
  浏览器的实际加载路径属平台生态事项（按 E543 的 lang_hold 口径，待
  OHOS 扩展生态就绪后接入）。
- `icedeb.xpi` 内嵌 zip mtime，归档 sha256 不可复现（已用逐条目比对兜底）。
- 未打包浏览器私有（Thunderbird）主题图标 `icons/icedeb-addon.png`（上游
  Makefile `ALL_FILES` 本就未包含该文件，与上游行为一致）。
