# DRAFT — 纯 Python console script 入口的可移植 wrapper：无 `__main__.py` 时禁用 `-m`、pip shebang 必须重写

> 状态: 草稿（Curator 判定 B 成立，A+B 组合主条 1/2；随 feat 分支交付；待查重复核/提升为 E 条目）。
> 域: 构建系统语义（PEP 517 console script / Python 模块执行 / 安装器 shebang 语义）| 层: L1（附 L2 佐证：配方树同型 ≥3 处实践）。
> Gate: authoritative CI attempt-1 PASS（conan create + test_package 全过；L2 裸跑 bin/ wrapper，无 conanrun）。
> 配对文件: `DRAFT-purepy-console-script-entrypoint-portable-wrapper.kv`（字段以 .kv 为准，本文为叙事展开与查重表）。
> 案例: kernel-hardening-checker 0.6.17.1；同型实例: py-cpuinfo 9.0.0（含 `__main__.py`，`-m` 形态对照）、adb-enhanced 2.8.0（`-m adbe.main` 模块入口形态）。

## 1. 真实问题（场景）

kernel-hardening-checker 0.6.17.1 是纯 Python CLI 工具，pyproject.toml 以
`[project.scripts] kernel-hardening-checker = "kernel_hardening_checker:main"`
声明入口，包内**无 `__main__.py`**。Conan 打包用 `python3 -m pip install
--prefix <staging> <src>` 在 staging 生成 `bin/kernel-hardening-checker`
console script。把 CLI 暴露给消费者时有两个坑：

1. 照抄近邻 py-cpuinfo 配方的 `exec python3 -m <pkg>` wrapper 形态——设备
   实测（2026-09-17，run upstream 源码根）：
   `PYTHONDONTWRITEBYTECODE=1 python3 -B -m kernel_hardening_checker --version`
   → `No module named kernel_hardening_checker.__main__;
   'kernel_hardening_checker' is a package and cannot be directly executed`。
   `-m` 要求包可执行模块 `__main__.py`，console script 型包没有 → CLI
   整体不可用。
2. 直接复制 staging 的 console script 到 `bin/`——pip 安装器把**安装解释器
   绝对路径**写进 shebang（本设备即
   `/storage/Users/currentUser/usr/local/bin/python3`，设备私有绝对路径）。
   py-cpuinfo 9.0.0 `manifest.yaml:79` 既有 in-archive 知识："pip 生成的
   console script shebang 指向构建机 Python 路径，不可迁移"。跨机执行即
   `bad interpreter: ...: No such file or directory`。

## 2. 根因（机理链，非单库 quirk）

pip / setuptools / CPython 三处稳定语义叠加：

1. **PEP 517 console script 语义**：`[project.scripts]` 入口（`pkg:main`）
   只让安装器生成入口脚本，不要求包提供 `__main__.py`；
2. **CPython `-m` 语义**：`python3 -m <pkg>` 执行 `pkg/__main__.py`，缺失
   即报 "is a package and cannot be directly executed"——wrapper 形态必须
   按"包是否可 `-m` 执行/入口是什么"选型，不能照抄邻近配方；
3. **pip 安装器 shebang 语义**：console script 的 `#!` 行内嵌安装解释器
   绝对路径（可移植性破坏 + 违反不硬编码设备私有路径基线）；而 conanrun
   环境非必然在场（CI L2 直接裸跑 `bin/`），wrapper 也不能依赖它注入
   PYTHONPATH。

上游自带跨环境答案：`bin/kernel-hardening-checker` 免安装 launcher 直接
`import kernel_hardening_checker` 后调 `main()`（官方注释支持免安装使用），
正确 wrapper 与之同型。

## 3. 方案（三形态判定树 + wrapper 模板）

**入口形态判定树**（看到 `No module named <pkg>.__main__` 或
`bad interpreter` 即命中本条）：

- 包含 `__main__.py` → `exec python3 -m <pkg> "$@"`（py-cpuinfo 9.0.0）；
- 入口为模块 `<pkg>.<mod>` → `exec python3 -m <pkg>.<mod> "$@"`
  （adb-enhanced 2.8.0 `-m adbe.main`）；
- 入口为 `pkg:main` 且包内无 `__main__.py` → 自解析 `/bin/sh` wrapper +
  `exec python3 -c 'import <pkg>; <pkg>.main()' "$@"`（本条主方案，
  kernel-hardening-checker 0.6.17.1）；
- 一律：不保留 pip console script 原 shebang，wrapper 重写为
  `#!/bin/sh` + 相对自解析，不依赖 conanrun。

**主方案 wrapper 模板**（完整实例见
`archives/k/kernel-hardening-checker/0.6.17.1/conanfile.py` `package()`）：

```sh
#!/bin/sh
WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"
SITE_PKG="$PREFIX_DIR/lib/<pyX.Y>/site-packages"   # <pyX.Y> 由配方 sys.version_info 推导
PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \
    exec python3 -c 'import <pkg>; <pkg>.main()' "$@"
```

与上游免安装 launcher 等价、免 conanrun（CI L2 裸跑 bin/ 通过）、零设备
绝对路径。

## 4. 验证探针（自包含，任何新 shell 可跑；2026-09-17 设备实跑通过）

```sh
PY="$(command -v python3 || echo /storage/Users/currentUser/usr/local/bin/python3)"
R="$HOME/tmp/oh-device-porting-v2/probe-purepy-console-script"   # OHOS 设备 /tmp 只读，探针用 $HOME 下 fleet tmp_root
rm -rf "$R" && mkdir -p "$R/probe-pkg/probe_pkg"
printf 'def main():\n    print("ok")\n' > "$R/probe-pkg/probe_pkg/__init__.py"
printf '[build-system]\nrequires=["setuptools"]\nbuild-backend="setuptools.build_meta"\n\n[project]\nname="probe-pkg"\nversion="0.1"\n\n[project.scripts]\nprobe-cli="probe_pkg:main"\n' > "$R/probe-pkg/pyproject.toml"

# 语义 A：无 __main__.py 的包 python -m 不可执行（合成探针，不依赖本 run 源码）
(cd "$R/probe-pkg" && "$PY" -m probe_pkg --version 2>&1 | tail -1 | grep -q '__main__' && echo SEMANTIC_A_OK)

# 语义 B：pip 安装器把解释器绝对路径写进 console script shebang
"$PY" -m pip install --quiet --break-system-packages --no-deps --no-build-isolation --prefix "$R/probe-stage" "$R/probe-pkg"
head -1 "$R/probe-stage/bin/probe-cli" | grep -q '^#!/' && echo SEMANTIC_B_OK
```

设备实测输出（2026-09-17，全新 ssh shell；fleet 新 shell PATH 无 python3，
由 PY 兜底行解析到 fleet 解释器）：

```text
PY=/storage/Users/currentUser/usr/local/bin/python3
/storage/Users/currentUser/usr/local/bin/python3: No module named probe_pkg.__main__; 'probe_pkg' is a package and cannot be directly executed
SEMANTIC_A_OK
#!/storage/Users/currentUser/usr/local/bin/python3
SEMANTIC_B_OK
```

正确形态的实证：本 run 交付的同型自解析 wrapper 随权威 CI attempt-1 PASS，
L2 消费者阶段直接裸跑 `bin/kernel-hardening-checker`（无 conanrun 注入）通过。

## 5. fallback 与边界（诚实权衡）

- **fallback 1（上游免安装布局直装，Scout 方案 A）**：`$PREFIX/<pkg>/**`
  按上游源码树安装 + 直接用上游 `bin/` launcher。权衡：绕开 wheel/staging
  与 console script 生成，但偏离 site-packages 消费契约与 Conan
  `package_info` 布局惯例（E319 族），消费者须特判，通用性差。
- **fallback 2（依赖 conanrun PYTHONPATH 的最简 wrapper）**：wrapper 只剩
  `exec python3 -c 'import <pkg>; <pkg>.main()'`，site-packages 交给
  conanrun 注入。权衡：**掩盖可移植性而非修复**——离开 conanrun 环境
  （裸跑 bin/、cron、脚本调用）即坏，仅作退路。

## 6. 反模式（forbid）

- 照抄 `exec python3 -m <pkg>` wrapper 而不验证包有无 `__main__.py`。
  Reason：`-m` 需要包可执行模块 `__main__.py`；console script 型包没有。
  Consequence：`No module named <pkg>.__main__ ... cannot be directly
  executed`，CLI 整体不可用。
- 直接复制 pip console script 并保留原 shebang。Reason：shebang 内嵌构建机
  解释器绝对路径（设备私有路径）。Consequence：跨机 `bad interpreter`，
  违反"不硬编码私有绝对路径"基线，审拒。
- wrapper 内硬编码设备绝对路径（解释器或 site-packages 写死）。
  Consequence：换机/换前缀即失效，不可移植、审拒。

## 7. 查重表（Curator 2026-09-17 实际检索：graph 542 kv / drafts 1711 文件 / 经验仓）

| 检索 | 命中 | 结论 |
|---|---|---|
| `grep -ril __main__` graph/drafts/经验仓 | 0 | 无覆盖 |
| `grep -ril console.script` graph | E319（+index.tsv） | 最相近：覆盖 pip wheel/staging + site-packages 布局 + console_scripts 放 bin/ + PYTHONPATH；其 rec_description 是"bin/ 复制 console_scripts"——**原样复制恰是本条 forbid_2 反模式**；不覆盖 shebang 不可迁移、`-m` 失效、wrapper 自解析三点 |
| `grep -il "console_script\|entry.point"` graph/*.kv | E319/E345/E354/E442 | 后三者（loadable module / Redis Tcl / host plugin）无关 |
| `grep -ril shebang` graph | 10 条（E037/E049/E143/E165/E293/E363/E435/E443/E463/E527） | mksh gpgrt-config 挂起、Autotools 解释器闭包、CI buildenv 门禁等，无一覆盖 pip console script shebang |
| `grep -rl "python3 -m"` graph | 7 条（E023/E056/E080/E219/E269/E319/E339） | locale/Python2 runner/测试分层等，不覆盖 `-m` 与 `__main__.py` 语义 |
| `grep -l "exec python3"` graph | 0 | 该 wrapper 形态此前仅存于配方树实践，未知识化 |
| 经验仓 `python/awscli-2.34.56.md` | — | 覆盖 python-require 打包与 OHOS subprocess 裸名，不含 `__main__.py`/shebang wrapper |
| in-archive：py-cpuinfo 9.0.0 `manifest.yaml:79` | — | 一行 shebang 知识（非正式条目），已并入本条 forbid_2 证据 |

新增价值：把配方树三处实践（py-cpuinfo / adb-enhanced / 本库）上升为带
判定树、fallback 与 forbid 的规则条目，并补 E319 的缺口（原样复制
console_scripts 的隐患）。

## 8. 关联

- `similar_to`: E319（python noarch pip staging 族；本条补其 console
  script shebang / 入口形态缺口）
- `principles`: P-ENV-001（环境变量与构建系统语义冲突陷阱——shebang、
  PYTHONPATH、`-m` 均属入口环境语义冲突面）
- 叙事关联 drafts：`DRAFT-VENDP-PUREPY-DEP-CLOSURE`（入口脚本相对引导
  site-packages 同型）、`DRAFT-multipledispatch-python-require-conan-staging`
  （PYTHONPATH 消费契约）
- 同型实例（L2 佐证 ≥3 门槛）：`archives/p/py-cpuinfo/9.0.0`、
  `archives/a/adb-enhanced/2.8.0`、`archives/k/kernel-hardening-checker/0.6.17.1`
  的 conanfile.py wrapper
