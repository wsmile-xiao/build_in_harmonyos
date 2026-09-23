# E429 — 纯脚本/补全脚本包被 conan-init 判为 autotools；G1 又强制要求 export_sources/apply_conandata_patches

> 草稿（`draft:true`，未入 index.tsv）。贡献者标识 AEA2，来源任务：pip-completion/20200731 适配。

## 错误特征

- `ohc-run.py conan-init <软件> <版本>` 打印 `构建系统: autotools`，生成的配方含
  `AutotoolsToolchain` / `autotools.configure()` / `autotools.make()` / `options={"shared": ...}` /
  `cpp_info.libs=["<包名>"]`；
- `ohc-run.py conan-verify` 首跑：
  ```
  G1: ❌ FAIL
    ❌ conanfile.py 缺少: export_sources() 方法
    ❌ conanfile.py 缺少: 补丁应用调用
  ```
  （即使 `conandata.yml` 里 `patches: {}`，即本版本零补丁，也照样 FAIL）
- `conan-init` 同时生成 `test_package/test.c` + `test_package/CMakeLists.txt`，而脚本包没有任何可链接符号。

## 触发条件

- 构建系统: 无构建族——Makefile 只有 `install`/`release` 之类目标（`bash` 补全脚本、数据/资源包、解释型 CLI 工具）
- 阶段: conan-init（骨架生成）→ conan-verify G1（配方完整性）→ G2（conan create 在 configure 阶段）

## 根因分析

1. **构建系统探测层**：探测优先级 manifest > 构建系统 > 源码统计。这类项目有顶层 `Makefile` 但没有任何编译规则，被判为 make/autotools，于是套用编译型骨架；R47 语言预检同样把 `Makefile + 无可统计源文件`（脚本文件常无扩展名，且规则 D.4 不把 bash 计入主体占比）判成 `c`。
2. **G1 完整性判定用字符串字面量**：`conan_verify.py` 的 G1 检查列表里含 `("export_sources", ...)` 与 `("apply_conandata_patches", ...)`，是「文本里出现即通过」的口径，与"本版本是否需要补丁"无关，所以零补丁的脚本包也必须保留这两个调用。
3. **test_package 默认 C 模板**：PF3/L0c/R34 要求 `test()` 有 `self.run` 真实执行，C 模板对无符号脚本包不可链接，必须换成 shell 断言脚本。

## 解决方案

### 推荐方案

按 `templates/conanfile-headeronly.py.tmpl` **变体 C（解释型脚本工具）**改写：

- 删除 `generate()`/`Autotools*`/`options.shared`；`build()` 只做脚本存在性与大小核验（不伪造编译日志），但**首行保留 `apply_conandata_patches(self)`**；
- **保留** `def export_sources(self): export_conandata_patches(self)`（无补丁时为 no-op，与 CI 补丁管道同构）；
- `package()` 用 `copy()` 落到包内 `share/bash-completion/completions/<命令名>`（**禁**写 `/etc/bash_completion.d`、`/usr/local` 等共享前缀，R49）；
- `package_info()`：`libs/libdirs/includedirs = []` + `resdirs = ["share"]`；`package_id()` 用 `self.info.clear()`（与 os/arch/compiler 无关）；
- `test_package/`：删 `test.c`/`CMakeLists.txt`，改为 `.sh` 断言脚本 + `test()` 中 `self.run(f"bash '{script}' '{file}'")`，真实 `source` 被测脚本并断言其行为（如 `complete -p <cmd>` 输出）。

### 禁止做法

- ❌ `autotools.configure()` / `AutotoolsToolchain(self)` 出现在无 configure 脚本的包里 → G2 必挂；
- ❌ `cpp_info.libs = ["<包名>"]` 声明并不存在的库 → 下游消费者链接失败；
- ❌ 为了让本地 pre-commit hook 的 `"bindirs" in src` 子串判定（L0k）不误报而删除 `self.cpp_info.bindirs = []`——CI 侧 `ci/conan/detect_bindirs.py` 已改 AST 判定（返回 0），删该行只会让 `cpp_info` 回落默认 `["bin"]` 与实际产物不符；正确做法是保留语义并记录 hook 待回填；
- ❌ 用 `package_type = "none"`（conan 2.29.1 枚举非法），脚本包写 `package_type = "unknown"` 或按先例不写。

## 验证

```bash
python3 scripts/ohc-run.py conan-verify <软件> <版本> 2>&1 | grep -E "G[0-4]:|缺少:"
#   期望 G1 PASS → G2 PASS（Packaged N files）→ G3 PASS → G4 PASS
python3 ci/conan/detect_bindirs.py archives/<l>/<软件>/<版本>/conanfile.py; echo $?
#   期望 0（非 CLI，无需 commands.json；加 commands.json 反而被 PF8「纯库包不应有 commands.json」拦）
```

实测：pip-completion/20200731 按此改写后 `conan create` rc=0、`package_id da39a3ee…`、
test_package A1–A7 全 PASS；同族已发布配方 docker-completion/29.5.2、brew-cask-completion/2.1 形态一致。

## 关联条目

- 相关: E524（依赖注入必须用 build_folder 私有 prefix——同属"不得污染共享前缀"家族）
- 备注: P001–P020 无对应原则条目，建议 promote 时新增「无构建族配方禁止套用编译型模板」原则
