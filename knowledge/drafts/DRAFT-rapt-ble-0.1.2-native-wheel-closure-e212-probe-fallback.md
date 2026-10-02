# DRAFT: pip 装的 OHOS 原生 wheel 闭包在 CI worker 上 import 必被拒（E212/E502）——test_package 的探测矩阵 + 静态回退模式

- **条目主题**：`python-require` 配方（pip staging）的运行时闭包一旦含 OHOS 原生 wheel，
  CI worker 的 hmmac 会拒**每个**解释器对该 `.so` 的 dlopen（`Permission denied`），
  而构建阶段本身成功。`test_package` 必须逐解释器探测、把静态产物校验作为回退，
  并用 `blocked_e212` 诚实标记上游套件；同时**不能**因此放过 R34/L1e 破坏性负测。
- **状态**：草稿（待知识库主编审核，拟提升编号 Exxx）
- **关联**：rapt-ble 0.1.2 适配（`archives/r/rapt-ble/0.1.2`，PR #13863）
- **同型/相邻条目**：E212（hmmac 拒用户路径 dlopen）、E219（别硬依赖非 HNP python 当 gate）、
  E502（worker 对用户目录 `.so` 的 dlopen/LD_PRELOAD 一律拒，与签名无关）、
  DRAFT-7939-gpgmepy-python-ext-selfsign-hmdfs（signature-based 假设——本条实测**不适用**）、
  已合并先例 cccolutils 1.5 / nanobind 2.13.0 / pillow 10.4.0 / jupyter-events 0.12.0

## 适用场景

`package_type = "python-require"`（或任何 `pip install --prefix` staging 的纯 Python 包），
运行时依赖闭包里**含原生扩展 wheel**。典型信号：

- CI `conan-build-test` 步骤红，日志里 `build()` 阶段全绿（pip 装好了 19 个 distribution），
  但 `test()` 的**第一条 import** 就失败：
  `ImportError: Error loading shared library .../bluetooth_data_tools/gap.cpython-312-aarch64-linux-ohos.so: Permission denied`
- 本地 `conan create` 完全通过（27 条消费者断言 + 7 个上游用例），CI 却红 → 容易误判为
  "配方随机失败" 而反复 `/rebuild`（E518 / DRAFT-11327 明文禁止）。
- `ls -Z <pkg>/lib/python3.12/site-packages/.../*.so` → `u:object_r:hmdfs:s0`（非 `hnp_file`）。

## 诊断步骤

```bash
# 1) 产物里到底有几个原生 .so（>0 就可能撞 E212；纯 Python 包常被误认为"无 .so"）
find <pkg>/lib/python3.12/site-packages -name '*.so' | wc -l        # rapt-ble: 14
ls -Z <pkg>/lib/python3.12/site-packages/bluetooth_data_tools/gap*.so
#   u:object_r:hmdfs:s0      ← worker dlopen 被拒的文件 label

# 2) 排除"签名被破坏"假设（DRAFT-7939）：本包 14 个 .so 全部自带 .codesign
python3 - <<'EOF'
import glob
sp = "<pkg>/lib/python3.12/site-packages"
bad = [p for p in glob.glob(sp + "/**/*.so", recursive=True)
       if b".codesign" not in open(p, "rb").read()]
print("missing .codesign:", bad)      # rapt-ble: []（全部已签名）
EOF

# 3) 本地 vs CI 的差别就是环境：本机同一 site-packages 直接 import OK
PYTHONPATH=<pkg>/lib/python3.12/site-packages python3 -c "import rapt_ble; print(rapt_ble.__version__)"
#   0.1.2（交互式真机运行环境比 worker 宽松，E502 原文）
```

## 真实证据（rapt-ble 0.1.2）

**CI（build #65061，worker `OpenHarmonyPCDeveloper-CI-039`，步骤 `conan-build-test`）**

```
ImportError: Error loading shared library
/storage/Users/currentUser/.conan2/p/b/rapt-*/p/lib/python3.12/site-packages/
bluetooth_data_tools/gap.cpython-312-aarch64-linux-ohos.so: Permission denied
```

- 失败点：`import rapt_ble` → `rapt_ble.parser`（`from bluetooth_data_tools import …`）
  → dlopen `gap.cpython-312-aarch64-linux-ohos.so`。
- `build()` 阶段成功（19 个 distribution 全部落盘），失败**只在 test 阶段的首次 import**。

**本地（同一台 aarch64 鸿蒙 PC，交互式运行时）**

```
E212PROBE interpreter=/storage/Users/currentUser/usr/local/bin/python3 verdict=ok tail=... -> 0.1.2
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 27, "passedCount": 27}
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "pytest",
  "discovered": 7, "executed": 7, "passed": 7, "failed": 0, "skipped": 0}
```

**模拟沙箱（本机 harness：只把 `_probe` 桩成返回 `Permission denied`，其余方法为配方真身）**

| 场景 | 结果 |
| --- | --- |
| 全部解释器被拒（=CI 情形） | 8/8 静态校验 PASS，`mode=static-elf-verify-e212`，上游 `status=blocked_e212`（passed/executed=0） |
| 删掉全部 `.so` | raise `E212 static verification failed: 7/8` ✅（负测仍有效） |
| 搬走 `lib/`（L1e 场景） | 探测前 raise `rapt_ble missing under site-packages` ✅（不会被回退"救活"） |

## 判据（为什么必须这样写）

1. **不能只试一个解释器**：worker 上开发机那种非 HNP python **不存在**（yarl 1.24.5 记录），
   而列在 `PATH` 首位的 HNP/sandbox 解释器被 hmmac 拒 —— 只试 `sys.executable` 会把
   "环境差异"写成"包坏了"。
2. **不能把回退写成无条件通过**（E502 forbid_3）：静态校验是**产物**证据（ELF/签名/PyInit/
   闭包自包含），不是 live 结果；因此标记里必须出现 `mode`/`status` 字段区分，
   且 live 计数一律记 0/不出现。
3. **不能牺牲 L1e**（R34）：CI 的破坏性负测搬走 `lib/`/`bin/` 后期望 `conan test` 失败；
   若回退分支只看"标记通过"，门禁会失真 —— 故 `site-packages/<pkg>` 缺失时**先 raise**。
4. **不要动缓存里的 `.so`**（E502 forbid_2）：签名与 dlopen 权限无关；对缓存包做 objcopy/重签
   只会制造"签名过期"的假象并污染共享缓存。本包 14 个 `.so` 已全部带 `.codesign` 仍被拒，
   正是排除该路线的直接证据。

## 方案（配方侧最小实现）

```python
def _candidates(self):        # 越不像沙箱越优先
    return [os.environ.get("RAPT_BLE_PYTHON"), os.environ.get("HMBS_PYTHON3"),
            "~/usr/local/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3",
            shutil.which("python3.12"), shutil.which("python3"), sys.executable,
            "/data/service/hnp/bin/python3", "/data/app/bin/python3"]

def test(self):
    sp = self._find_site_packages(self.dependencies["rapt-ble"].package_folder)
    if not sp or not os.path.isdir(os.path.join(sp, "rapt_ble")):
        raise ConanException("rapt_ble missing under site-packages")   # ← 保住 L1e
    for cand in self._candidates():
        ok, tail = self._probe(cand, sp)          # tail 只截尾部（E502 forbid_1）
        self.output.info("E212PROBE interpreter=%s verdict=%s tail=%s" % (cand, ok, tail))
        if ok: return self._live(sp, cand)        # 真跑：消费者断言 + 上游 pytest
    if str(self.settings.os) == "OHOS" and "Permission denied" in "\n".join(tails):
        checks = self._static_verify(sp)          # 8 项字节级校验（无 readelf 依赖）
```

- 静态校验 8 项：闭包 import 目录 / dist-info 计数（自包含）/ `.so` 数量 / ELF 魔数 /
  `.codesign` / cpython 扩展 `PyInit_<mod>` / 动态串含 `libc|libc++|libpython` /
  `rapt_ble-<ver>.dist-info/METADATA` 的 `Name`+`Version`。
- 参考实现：`archives/r/rapt-ble/0.1.2/test_package/conanfile.py`。

## 注意事项

- **上游 pytest 与 live import 同命运**：二者都要 dlopen 同一个闭包，因此回退时上游标记
  只能记 `blocked_e212`（7/7 已在真机实测通过，如实写在 notes/PR body），
  不能用"跳过测试"或"无条件通过"糊过去。
- **`test_package/MANIFEST.yml` 要说明两种模式**，否则审查者看到 `passedCount: 8` 会误以为
  消费者断言缩水。
- 若某轮 CI 的探测输出**不是** `Permission denied`（例如解释器缺失、site-packages 布局变化），
  不要归因 E212：带 worker id/build number 上报环境问题。

## 推广价值

- 所有 `python-require` / pip staging 配方，只要闭包含原生 wheel：**先数 `.so`**，
  再决定测试形态（live 会绿，但要写清 worker 上的回退路径与诚实标记）。
- 通用判据：**"本地 conan create 绿" ≠ "CI 必绿"**；两者差别可能正是 E212/E502 的 loader 边界。

## 查重关键词

python-require、原生 wheel、native wheel、dlopen、Permission denied、hmmac、E212、E502、
用户路径 `.so`、hmdfs、`.codesign`、解释器探测、`E212PROBE`、静态产物校验、
`elf-static-fallback`、`blocked_e212`、L1e、R34 破坏性负测、`conan create` 本地绿 CI 红、
pip `--prefix`、site-packages、package_folder、HNP python、DRAFT-7939、cccolutils 1.5
