# DRAFT — 纯 Python 依赖闭包 vendor 模式：固定 SHA256 官方 sdist 进包内 site-packages + 相对 sys.path 引导

> 状态: 草稿（Curator 判定 B 成立·条件通过——打回项已补齐，随 feat 分支交付；待查重复核/提升为 E 条目）。
> 域: 依赖闭包 | 层: L2 跨库工程模式（配方层桥接/消费模式）。
> Gate: authoritative CI attempt-2 PASS（conan create + test_package 全过，Summary 1/1 100%）。
> 配对文件: `DRAFT-VENDP-PUREPY-DEP-CLOSURE.kv`（字段以 .kv 为准，本文为叙事展开与查重表）。
> 案例: dehydrated-hook-ddns-tsig 0.1.4（dnspython vendoring）；同型实例：pyvolumio 0.1.5、adb-enhanced 2.8.0、airthings-ble 1.2.0、aiohttp-fast-zlib 0.3.0。

## 1. 真实问题（场景）

dehydrated-hook-ddns-tsig 是纯 Python 单脚本（dehydrated 的 DNS-01 challenge hook），
运行依赖 dnspython。OHOS 设备 Python 3.12.9 无该模块（探针：
`python3 -c "import dns"` → `ModuleNotFoundError: No module named 'dns'`，
Curator 本轮实测复现），而 ConanCenter 无 dnspython 配方、仓 `archives/` 亦无。
`conan create` 可以通过（构建期只做 py_compile），但任何真实调用在目标机必失败。

依赖闭包的三条常规出路全部不通：
1. Conan `requires` — R36 要求依赖先发布到制品仓，无配方的依赖无法满足；
2. 新建 `archives/d/dnspython/` 独立移植 — 超出本库 run 的写入边界（他库目录）；
3. pip 安装到设备系统 Python — 污染宿主环境，且设备 Python 属用户空间，不可依赖。

## 2. 根因

"纯 Python 宿主 + 运行依赖不在 Conan 图内"是依赖闭包缺口：Conan 的依赖解析只覆盖
配方化的 C/C++（及部分 Python）依赖，纯 Python 脚本类宿主的运行依赖默认游离在
依赖图之外；无配方时 R36/制品仓机制无从介入，run 写入边界又禁止越界建他库目录。

## 3. 方案（本条申报的规则）

在**目标包内** vendor 依赖，四个要点（对应 conanfile.py/patch 的可复用做法）：

1. **固定来源**：依赖官方 PyPI sdist 的 URL+SHA256 写成 conanfile.py 模块常量
   （本例 dnspython 2.8.0，`181d3c69…`），`source()` 里 `get(self, URL, sha256=…,
   strip_root=True, destination="vendor/<dep>")`。
2. **装入包内**：`package()` 拷贝到 `lib/python3.12/site-packages/<dep>/`，
   `copytree(..., ignore=ignore_patterns("__pycache__"))`。
3. **运行时闭包**：入口脚本以**相对路径**引导
   （`os.path.dirname(os.path.realpath(__file__))/../lib/python3.12/site-packages`
   插到 `sys.path[0]`，补丁携带、不写设备绝对路径）；`package_info()` 另设
   `runenv_info.append_path("PYTHONPATH", …)` 给 Conan 消费者双保险。
4. **产物卫生**：`build()` 的 py_compile 校验设 `PYTHONPYCACHEPREFIX` 指向 build
   目录，否则 `__pycache__/*.pyc` 会被 copytree 打进包。

**依赖 URL/SHA256 必须放 conanfile.py 常量，不放 conandata.yml**（机理精确表述）：
- CI 的 mirror-fallback 仅重写"**已知域名的单值 `url:` 行**"；files.pythonhosted.org
  在镜像表中**无镜像可加、行保持原样**——pyvolumio/aiohttp-fast-zlib 的
  pythonhosted 自定义 key URL 通过 CI 即既有反例，"任意 URL 都会被 mirror-fallback
  改写"的说法不成立。
- 真正的任意改写者是 **predl**：其正则提取**任意** https URL（**含注释行与自定义
  key**），并对全文做子串 `file://` 替换——jwt-cpp 0.7.1 实证注释中的裸仓库 URL
  被误提取并子串污染完整归档 URL（403/NotADirectoryError）。
- 结论不变：把 vendor 源留在 conandata.yml = 与 CI 改写机制强耦合；conanfile.py
  常量完全绕开该耦合面，且 sha256 语义清晰（"源"与"vendored 依赖"在检索时天然可分）。

## 4. 验证探针（自包含，任何新 shell 可跑）

```sh
# 适配前（缺口在场的证据）
python3 -c "import dns" 2>&1 | grep -q ModuleNotFoundError && echo PRE_GAP_OK

# 适配后（闭包成立的证据；<pkg> 换成包目录）
ls <pkg>/lib/python3.12/site-packages/dns/__init__.py
python3 -c "import sys; sys.path.insert(0,'<pkg>/lib/python3.12/site-packages'); \
  import dns; assert dns.__file__.startswith('<pkg>'); print('vendored', dns.version.version)"
# 期望输出: vendored 2.8.0

<pkg>/bin/dehydrated-hook-ddns-tsig --help >/dev/null && echo HOOK_OK   # 期望 exit 0
```

本 run 实测：权威 CI attempt-2 的 test_package 即执行同型断言并 PASS
（L1a/L1b/L1e 全过；L1e 破坏性反证：移走 bin/ lib/ 后测试必失败）。

## 5. fallback 与边界（诚实权衡）

- **conandata 自定义 key + predl 成功路径**（fallback，pyvolumio 的 `python_deps:`、
  aiohttp-fast-zlib 的 `vendor_wheels:` 先例，均 url+sha256）：predl 预下载命中时
  同样可用。权衡：依赖 worker/predl 网络，cache miss 或无 curl 即失效；且
  conandata.yml 是 CI 活动改写对象，配方与 CI 内部机制强耦合，脆弱于 conanfile.py
  常量方案。
- **规避 ≠ 修复**：使用侧绕开依赖触发路径的用法（如 iscpy 场景改在 conf 直配
  key_name/key_secret）只是规避，不是依赖闭包修复，不能替代本模式。

## 6. 反模式（forbid）

- 在 conandata.yml（sources 之外或注释）写 vendor 依赖 URL 并期望 CI 不改写。
  Reason：predl 任意提取 + 子串替换（jwt-cpp 实证）；mirror-fallback 对已知域名
  单值 `url:` 行改写。
  Consequence：cache miss/无 curl 时 source() 失败（403/NotADirectoryError）或
  sha256 校验错文件；"官方源"与"vendored 依赖"在元数据层不可区分。

## 7. 查重表（Curator §1.1 逐项对比结论）

| 既有条目 | 其覆盖点 | 与本条差异（不重叠的证据） |
|---|---|---|
| E277 | C 库自带 vendored 子项目 → build() 编译到 staging | 构建期 C 桥接，非纯 Python 运行依赖闭包 |
| E271 | 单文件 release 资产免解压安装 | 资产获取形态，非依赖闭包 |
| E372 / E2149 | 配方级 hash-bound 官方 HTTPS 优先 + authority HTTP 回退 | "源获取"回退设计，非"无配方运行依赖"闭包 |
| E415 | mirror-fallback 原地改写 conandata.yml → CI 后必须恢复 | 执行期副作用管理 + L4 误扫；本条是**设计期规避**（avoidance-by-placement：URL 放 conanfile.py），与"事后恢复"互补 |
| E549（draft 族） | mirror-fallback 仅改已知域名单值 `url:` 行 | 本条引用其机理边界并给出 pythonhosted 反例；不覆盖 vendor 模式本体 |
| DRAFT-jwt-cpp-…-conandata-comment-url-predl | predl 任意提取含注释 + 子串改写 | 本条 forbid 的机理证据源；不覆盖 vendor 模式本体 |
| E049 | shebang 可移植 | 覆盖 0001 补丁的 shebang 半边；sys.path 引导半边并入本条 |
| E044/E050/E212/E219/E271 | Python 打包路径/RPATH/HMDFS/verify-elf | 均非依赖闭包 |

graph（540 条）+ drafts（473 个 .kv/.md）+ 经验仓 dependency/other 抽查均无覆盖
（检索词与命令见 Curator 报告 §1.1）。

## 8. 关联

- `similar_to`: E277, E271, E372, E415, E549
- `principles`: P010（RPATH 必须覆盖所有 NEEDED——Python 类比：sys.path/PYTHONPATH
  必须覆盖 vendored 模块层，否则目标机 ImportError）、P013（平台/环境限制必须降级
  到可用方案——闭包缺口不可解除时降级为包内 vendor，而非重试或污染宿主）
- 经验仓关联条目：EXP-2（predl 回退与 conandata 改写/还原边界）、EXP-4
  （PYTHONPYCACHEPREFIX 防 .pyc 入包）
- L2 同型实例（≥3 门槛满足）：`archives/p/pyvolumio/0.1.5`、`archives/a/adb-enhanced/2.8.0`、
  `archives/a/airthings-ble/1.2.0`、`archives/a/aiohttp-fast-zlib/0.3.0` 的 conanfile.py
