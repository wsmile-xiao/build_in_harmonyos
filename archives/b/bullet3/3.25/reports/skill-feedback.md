# SKILL 反馈 — bullet 3.25 适配过程（2026-09-25）

## P1：`lang-preflight` 对「C++ 库 + Python 打包脚本」误判为 `python`（R47 假阳性）

**现象**（真实命令与输出）：

```bash
$ python3 scripts/ohc-run.py lang-preflight bullet 3.25 --src <src>
{
  "status": "env_unsupported",
  "error_detail": "任务标记 cpp，实测源码为 python（setuptools），无法按 cpp 适配——按协议 v0.8 §7.2 交平台语言迁移",
  "detected_language": "python",
  "language_evidence": {
    "build_system": "setuptools",
    "manifest": "setup.py 存在（python 打包 manifest）",
    "source_stats": "源文件 1559 个（cpp:781, python:609, lua:86, c:67），主体占比 50%"
  }
}
rc=2
```

**误判原因**：`scripts/ohc/lang_detect.py::_manifest_scan()` 中 manifest 判定顺序为
`Cargo.toml → {pyproject.toml, setup.py, setup.cfg} → go.mod → …`，命中 `setup.py` 即直接返回
`("python", "setuptools")`，**先于**构建系统（CMake）与源码统计；且源码统计把 `examples/pybullet/**`
的 609 个 `.py` 计入分母，得出"主体占比 50%"。

**真实事实**（同一份源码）：

```bash
$ find src -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.c' \) | awk -F. '{print $NF}' | sort | uniq -c
    419 h
    229 cpp
     11 hpp
      1 c
$ ls CMakeLists.txt VERSION            # 真实构建系统 = CMake；setup.py 只服务 pybullet 绑定（配方 BUILD_PYBULLET=OFF）
```

**违反技能自身边界规则**（R47 附录 D.4）："辅助脚本（构建脚本是 python 等）不算主体语言"、
"绑定类包（pybind11 包装 C++）→ 判 cpp"。bullet 正是"C++ 库 + setup.py 提供 Python 绑定"的典型。

**危害**：一个 100% 的 C++ 库会被直接判 `env_unsupported` 并**自动写终态 result.json**（draft:false），
任务被误杀；本次靠人工核验（源码构成 + 构建系统 + 发布物为 C++ 静态库）才继续。
（副作用：终态已写导致后续 R46 里程碑草稿全部被跳过，最后须用 `result --force` 纠偏。）

**建议修复**：
1. `setup.py`/`pyproject.toml` 只有在**没有 C/C++ 构建系统**（CMakeLists.txt / meson.build / configure.ac /
   Makefile）时才作为语言依据；两者并存时应降级为"binding"证据，按 C/C++ 族判定（并在
   `language_evidence.manifest` 注明绑定关系）。
2. 源码统计应排除 `examples/`、`data/`、`bindings/` 等示例/资源目录；或对声明了 C/C++ 构建系统的工程
   仅在统计与构建系统矛盾时才报 `mixed`。
3. 终态写入前增加"反证"：若存在 `CMakeLists.txt`/`meson.build`，或 `requirements()` 为空且产物为
   C/C++ 静态库，则不允许判定 `python`。

## P2：源码下载无进度/超时反馈，国内到 GitHub 带宽极低

**现象**：`conan create` 卡在 `bullet/3.25: Calling source() in …` 近 10 分钟无任何输出；
实测下行 `32988 B/s`（140MB tarball ≈ 70 分钟）。无进度、无超时、无已下载字节数提示。

```bash
$ curl -sL -o /dev/null -w "http_code=%{http_code} downloaded=%{size_download} speed=%{speed_download} B/s\n" --max-time 20 <codeload url>
http_code=200 downloaded=661611 speed=32988 B/s
```

**绕行（有效，已实测，建议写入 SKILL/compile-guide）**：使用 conan 官方 **sources download cache**
复用已核验 tarball，**无需改配方**：

```bash
# 缓存文件必须放在 <cache>/s/<sha256>（SOURCE_BACKUP 子目录是 "s"，不是 "sources"）
mkdir -p $CACHE/s
cp bullet3-3.25.tar.gz $CACHE/s/c45afb6399e3f68036ddb641c6bf6f552bf332d5ab6be62f7e6c54eda05ceb77
conan create <recipe> -pr:h=… -pr:b=… -cc core.sources:download_cache=$CACHE
# 输出: "bullet/3.25: Source <url> retrieved from local download cache"
```

> 注意：`core.*` conf **不能**用 `-c` 传（报 `[conf] 'core.*' configurations are not allowed in
> profiles`），必须用 `-cc/--core-conf`；缓存目录放错层（`sources/` 而非 `s/`）会被静默忽略并重新下载。

## P3：已发布同版本库的"上游测试集成"存在流程死结（R37/L0j × R51）

**现象**：`bullet/3.25` 已在制品仓发布，且本仓 `conanfile.py` 与其逐字节一致。要把上游 ctest
集成进 `build()`（如 `cmake.test()`）必须改 `conanfile.py` → 触发 CI **L0j（R37）**：
cnb.cool 不支持同版本多 recipe revision（409）→ 必须递增版本号。而 `3.25.1` 已被同族"双精度变体"
占用，只能跳到 `3.25.2`，与"目标版本 3.25"的任务口径冲突。

**本次处置**：保持配方不动（`BUILD_UNIT_TESTS=OFF`），上游套件用**独立构建面实测**并在
`notes.md`/`test_package/MANIFEST.yml`/`reports/test-report.md` 如实申报。

**建议**：SKILL 明确该场景默认处置（默认 = 独立构建面实测 + 申报；仅当用户显式要求"上游测试进 CI"
时递增版本号），并在 `finish`/`submit` 的 HANDOFF 中主动提示"该版本已发布 → 修改配方将触发 L0j"。

## P4：本地 W3 的三处框架缺陷（本次实测）

1. **JC `full` 模式必然误伤**：W3 的 JC 检查优先用 `git diff origin/main...HEAD`；本地开发分支
   未提交变更时该 diff 为空 → 回退 `full`（`git ls-files` 整仓扫描）→ 命中**他人已合入 main 的残留
   标记**（本次实测：`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、
   `archives/k/kics/2.1.20/.staging-verified`）→ JC1/JC5 双 fail，与本包无关。
   绕行：本地按 CI 同口径写 `pr.diff`（junk_check.sh 内置优先级 1 = prdiff 模式），只校验本 PR 文件清单。
   **建议**：W3 驱动在增量 diff 为空且工作区有未提交变更时，自动生成 pr.diff（或提示用户），
   避免 agent 误以为是自己引入了垃圾文件。

2. **`finish` step 10 就绪预检与 JC/铁律自相矛盾**：预检要求存在 `.staging-verified` 与 `packaging/`，
   但 `.staging-verified` 不在 JC5 白名单（属于会被拦截的 archives 隐藏文件），`packaging/` 又与
   R20「禁止手动打包」冲突。本次未创建这两项（JC 通过、conan create 已覆盖打包验证）。
   **建议**：删除或改造 step 10 的这两个检查项。

3. **`gen_summary` 报错**：`⚠️ gen_summary 失败: 'str' object has no attribute 'append'`（Step 8/10，
   非致命）。**建议**：修 `SUMMARY.md` 生成器的类型错误。

4. **`clean-verify` 的 G0 硬编码 autotools**：`configure_cmd = "./configure"`，对 CMake/Meson 工程必然
   `exit 127`（实测 `/data/service/hnp/bin/bash: ./configure: No such file or directory`）。
   虽然是"非阻塞"，但会产生误导性的"G0 失败"告警。**建议**：按 manifest `build_system` 分派
   （cmake → `cmake -S . -B build` 等），或对非 autotools 工程直接标 SKIP。

## P5：W3 的 CI 脚本改写 `conandata.yml` 后**未还原**，并残留备份文件（会把垃圾带进 PR）

**现象**（W4 独立审计发现，本次实测）：`finish` 的 W3（`ci/conan/build_and_test.sh`）执行后：

```bash
$ git diff -- archives/b/bullet/3.25/conandata.yml
-  url: "https://github.com/bulletphysics/bullet3/archive/refs/tags/3.25.tar.gz"
+  url:
+    - "https://gh-proxy.com/https://github.com/bulletphysics/bullet3/archive/refs/tags/3.25.tar.gz"
+    - "https://github.com/bulletphysics/bullet3/archive/refs/tags/3.25.tar.gz"

$ ls archives/b/bullet/3.25/ | grep -E 'orig|bak'
conandata.yml.orig
conandata.yml.ghfast-bak
```

- 改写后的 `conandata.yml` 会**直接进 PR**：违反 R39（官方源）+ 触发 CI L0j（R37）；
- `.orig` / `.ghfast-bak` 命中 JC1 垃圾模式（`.orig`、`.ghfast-bak`）与 PF7 静态闸；
- 对比：`conan-verify` 的 G2 注入是**有还原的**（并会清理陈旧 `.ghfast-bak`），W3 路径没有。

**修复**：`git checkout -- <conandata.yml>` + 删除两个备份文件（本次已做，修复后重新审计通过）。

**建议**：把 `conan-verify` G2 的"备份 + finally 还原 + 陈旧备份清理"逻辑同样移植到
`ci/conan/build_and_test.sh` 的预下载改写路径（v12.17 只覆盖了部分脚本），或在 W3 结束时由
`workflow_checks.run_local_ci()` 统一做"工作区还原校验"（比对 `git status` 中的
`conandata.yml`/`*.orig`/`*.bak`，发现即自动还原并告警）。

## P6：W4 审计工具的两个落地缺口（本次实测）

1. **`pre_pr_audit.py generate` 只认「已提交」的 diff**：它用 `git diff origin/main...HEAD`，在
   "用户要求停在 commit 之前"的场景下 diff 恒为空 → 报 `ERROR: 没有变更文件，无需审计`，W4 无法执行。
   本次由 agent 按同一 JSON schema **同构生成**审计输入（metadata 注明原因），并把结论落到
   `reports/audit-result.json`。**建议**：`generate` 增加"工作区模式"（`--worktree`：用
   `git status --porcelain` + untracked 清单），使 W4 在"未提交但已就绪"的工作流下可用。

2. **`pre_pr_audit.py report` 只打印、不落盘**：而 `submission.py` Gate 3/4 要求审计结论必须存在于
   `<version>/reports/audit-result.json`。本次由 agent 手工把子任务结论写入该路径并附
   `provenance`（工具/方法/两轮记录/被检文件 sha256，满足 R52 证据一致性）。
   **建议**：`report` 直接写 `reports/audit-result.json`（含 input 文件路径与 sha256 溯源），
   避免 agent 手写造成的"审计证据可伪造"质疑。

---

## 补充：本次交付的最终命名决议（2026-09-25 17:2x）

会话早期以 `bullet`（与制品仓既有包同名）推进，故第 P3 条记录了 R37/L0j 死结。任务方随后明确目标库登记名为 **bullet3**，本次交付遂按
`目录 archives/b/bullet3/3.25` ↔ `conanfile.name = "bullet3"` ↔ `分支 feat/bullet3-3.25` 三者一致落地：

- `bullet3/3.25` 在制品仓**不存在** → L0j 视为"首次发布"，**P3 的 R37 死结随之消失**（不再受"改动配方必触发版本冲突"约束）；
- 制品仓既有的 `bullet/3.25`、`bullet/3.25.1`（同一上游的旧命名包）本 PR 未改动，不影响任何既有下游；
- 由此也可看出 P3 建议的价值：当同一上游在既有包名下已发布时，**改包名**与**递增版本号**是两条合法出路，SKILL 宜在 HANDOFF/文档中并列给出。
