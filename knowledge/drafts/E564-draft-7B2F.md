# E564-draft-7B2F — 大型 Debian Blend 的 R47 预检分流（识别为 metadata/registry 包）

## 错误面
- **触发**：lang-preflight（`scripts/ohc/lang_detect.py`）对**大型**纯打包元数据型
  Debian Blend 源码包做语言预检
- **阶段**：configuration（checkout 后、进入适配主流程前的 R47 预检）
- **签名**：`detected_language: "c"` + `source_stats: 无源文件可统计` +
  `include /usr/share/blends-dev` + 规模特征（45 个 `Package:` 声明（全 `Architecture: all`）/
  46 个 tasks 文件 / 42 段落 tasksel desc / 38 个 dependency_data JSON）

## 识别
- severity: 2（🟡medium —— 检测器按"构建系统优先"归入 c/cpp 族，会误导后续路由决策）
- category: detection, build-system, make, packaging, ohos
- 关联：E560（同族小型 blend debian-pan 0.4 的检测器盲区现象）；
  E565（配套的大规模批量校验套件）；Issue #2884 对应 draft（blend→Conan 通用映射方法）

## 诊断
与 E560 的小型 blend（debian-pan 0.4，35 文件 18 任务）相比，**规模变大不改变性质**：
debian-science 1.15 有 97 个文件、45 个 `science-*` 二进制元包、46 个 tasksel 任务文件、
42 段落 tasksel desc（41 个 `Key:`）、38 个历史版本 JSON（0.1→1.15），但仍是**纯打包元数据**：

```console
$ grep -c '^Package:' debian/control                      # → 45（全部 Architecture: all）
$ ls tasks/ | wc -l                                       # → 46
$ grep -c '^Task:' debian-science-tasks.desc              # → 42
$ grep -c '^Key:'  debian-science-tasks.desc              # → 41
$ grep -c '^Architecture: all' debian/control             # → 45
$ find . -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' \) | wc -l   # → 0
```

顶层 `Makefile` 与 `debian/rules` 各只有一行 `include /usr/share/blends-dev/…`，
构建依赖 `blends-dev (>= 0.7.5~)` + `debhelper-compat (= 13)`（Debian 特有）。
lang-preflight 实测（exit 0）：

```json
{ "expected": "cpp", "detected_language": "c",
  "language_evidence": { "build_system": "make",
    "manifest": "顶层 Makefile（无更强 manifest）",
    "source_stats": "无源文件可统计" } }
```

### 大型 blend 四重规模识别特征（分流判定时逐项核对）
1. **control 多 Package 声明且全为 arch:all**：`grep -c '^Package:' debian/control` ≥ 40，
   且 `grep -c '^Architecture: all'` 与之相等（本例 45 == 45），全部 `<blend>-*` 前缀；
2. **tasks/ 大量 Deb822 任务文件**：`ls tasks/ | wc -l` ≥ 40，每文件含
   `Task:`/`Install:`/`Description:` 字段；
3. **tasksel desc 的层级结构**：段落数 ≥ 40，含 1 个父任务（无 `Key:`）+
   N 个 `Key: <blend>-<topic>` 子任务；
4. **dependency_data 版本序列 JSON**：`<blend>_*.json` 覆盖历史版本序列，
   最新版键集合与 tasks/ 文件名集合一致（本例 46 == 46）。

> **⚠️ 关键分流结论**：四重特征齐备 = 纯打包元数据（描述文本 + 依赖声明）。
> 但这**不等于"无法适配"**——正确的路由是 **metadata/registry Conan 包**：
> 真实价值在依赖图 + task/desc 定义 + tasksel 元数据，可用单个 recipe 如实装载。

## 方案
识别为**纯打包元数据**后，走 metadata/registry 包路径（**不是**硬做 C/C++ 配方，
**也不是**一律 `env_unsupported` 终止）：

```python
# 单 recipe，data/metadata 包
package_type = "unknown"
settings = "os", "compiler", "build_type", "arch"   # CI L0 门禁；数据包无语义

def requirements(self):
    pass   # 零 Conan requires：Debian Depends/Recommends/Suggests 是 OS 包选择
```

- `package()` 装**真实上游产物**：`tasks/*` 原文 + tasksel desc 原文 +
  官方依赖快照原文 + `build()` 纯解析派生的 `registry.json` + `licenses/copyright`；
- `registry.semantics` 记录 blends 旧格式语义（无 `Format:` 头 → 文件级 `Depends:`
  降级为元包 `Recommends:`，元包另 `Depends: <blend>-tasks (=version)`）；
- R47 的 `detected_language` 仍按 §4.6 如实填 `c`（c↔cpp 兼容族），但任务
  **继续走适配主流程**；
- 参考实现：`archives/d/debian-science/1.15/`（本地 `conan create` RC=0，
  test_package 33 项断言全 PASS）；同族先例 `archives/d/debichem/0.0.12`、
  `archives/d/debian-parl/1.9.33+nmu1`（CI PASS）。

验证命令：

```bash
conan create archives/d/debian-science/1.15 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# → RC=0；test_package: ALL checks PASSED（33/33）
```

## 禁止
- ❌ 硬编 conan 空壳配方（R34/R8）——零 API/二进制可调用，硬做=造假，
  W3/CI 必然失败且被审计按欺骗类一票否决（R52）
- ❌ 把 Debian 包名机械复制进 Conan `requires` —— Debian 包名 ≠ Conan 包名，
  1976 条 OS 包选择（含 `r-cran-*`/`python3-*`/`lib*-dev` 等 Debian 专有命名）
  会造出虚假且不可满足的依赖图（PF4 依赖闸亦会拦截）
- ❌ 把"零 C/C++ 源码"直接等同于"无法适配"——会漏掉已证可行的
  metadata/registry 包路径（Issue #2884 两个 CI PASS 实例）
