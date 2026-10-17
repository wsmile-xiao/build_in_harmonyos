# draft-ci-l0k-naive-grep-package-type-application-in-comments

> Status: **Draft**（待审核 promote）| severity: `2` | category: `ci|tooling` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-ci-l0k-naive-grep-package-type-application-in-comments.kv`

---

**匹配关键词**：L0k, commands.json, R38, package_type, application, detect_bindirs.py,
quality gate, build_and_test.sh, docstring, grep

## 症状

一个 `package_type = "library"`、没有任何可执行文件的库配方，本地跑同源门禁直接 L0 红灯：

```text
[step] L0k: Checking commands.json for CLI tools (R38)...
[fail] L0k: CLI tool detected but commands.json missing (R38)
[hint] 此软件构建可执行文件, 应在软件级别目录下创建 commands.json:
[fail] pd-libdir/1.11 — L0 quality gate failed: commands_json_r38
```

`detect_bindirs.py` 返回 0（因为 recipe 里是 `bindirs = []`），recipe 也确实没有 `package_type = "application"`。

## 根因

L0k 判定 CLI 工具用三个启发式：

1. `python3 ci/conan/detect_bindirs.py <conanfile>` —— AST 解析，**能正确忽略** `bindirs = []`；
2. `grep -cE 'RUNTIME\s+DESTINATION\s+bin\b|dst\s*=\s*["'"'"']bin["'"'"']' <conanfile>`；
3. `grep -c 'package_type.*=.*"application"' <conanfile>`。

后两条是**无上下文的文本 grep**，不区分代码、注释与 docstring。本包 recipe 的
`_pd_include_dir()` docstring 里有这样一句解释依赖形态：

```python
puredata/0.54.1 is package_type="application", so it publishes no
```

注释里的字面量同样命中 `package_type.*=.*"application"`，于是被判成 CLI 工具 →
强制要求软件级 `commands.json` → 未提供即 L0 fail。

真正的 R38 口径是「构建产物含可执行文件」。本包的产物 `libdir/libdir.pd_linux` 是
`ET_DYN` 共享对象、**没有 `main()`**，只能由 `pd -lib libdir` 加载（`pd` 属于 `puredata`
包，那里已经声明了 commands.json），属库形态。

## 推荐方案（`avoid-package-type-application-literal-in-comments + run-local-ci-gate-before-push`）

1. 把注释/docstring 里的 `package_type="application"` 改写成自然语言，
   例如 `puredata/0.54.1 is declared as an application package, so it publishes no ...`
   —— 保留说明价值，去掉会被 `grep -c` 命中的字面量形态（`grep -c` 只数匹配行数）。
2. 需要说明依赖形态时，避免「`package_type` + `=` + `"application"`」三段连续出现。
3. **改完必须本地跑同源门禁复验**，这是最省时间的动作：

   ```bash
   CI_PACKAGES=archives/<pkg>/<ver> CI_BRANCH=feat/<pkg>-<ver> \
   CONAN_PROFILE=ohos-aarch64-wsl zsh ci/conan/build_and_test.sh
   ```

4. 判定是否真需要 commands.json 的正确口径是「产物能否作为命令调用」：dlopen 加载的
   插件（无 `main()`）不算，不要为了过门禁伪造一个不存在的命令。

## 验证

`pd-libdir/1.11` 本地同源门禁首次跑即复现 `[fail] L0k ... commands_json_r38`；把 docstring
里唯一一处 `package_type="application"` 改写为「declared as an application package」后重跑，
**L0 全绿**（test_package 22/22 断言通过，L1 / L1e / L4 / L5 全过）。修复前 100% 复现。

---

*本文件由 `knowledge/drafts/DRAFT-ci-l0k-naive-grep-package-type-application-in-comments.kv` 字段派生；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
