# DRAFT: header-library 的 bindirs 永不进 conanrun PATH —— test_package 裸调二进制恒 127

- **草稿 ID**: DRAFT-E691-header-library-run-false-bindirs-not-in-conanrun-path
- **来源库**: simstring 1.0（OHOS PC aarch64, conan 2.29.1）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **同族条目**: E690（下载双面 sha）、E299（source 期失败分层）
- **仓内先例**: abiword-plugin-* 族（test() 传 `$1`，多例过 CI）、aa3d（application + 裸命令名过 CI）

## 问题（打包完好、直跑健康，五查却全 127）

simstring 1.0 round4：`conan create` 走到 test_package——消费者 C++ 测试
`12 assertions OK` 全过，随后 `test.sh` 五查全部：

```
[TP] FAIL version banner (rc=127)
[TP] FAIL build phase (rc=127)
…（5/5 rc=127）
ERROR: … Error in test() method, line 44  ConanException: Error 1 while executing
```

三步取证把"看起来像打包/装载坏了"的表象逐一排除：

```sh
# ① 包内实物完整
conan cache path "simstring/1.0@ohpcd/stable:<package_id>"   # 注意带 pid（§二.17）
#   → p/.../p/bin/simstring (227840B) + include/simstring/*.h ×6 + share/doc
# ② 打包二进制直跑健康
<pkg>/bin/simstring -v     # → SimString 1.0 … rc=0（装载器无问题）
# ③ conanrun 之后命令找不到（逐字复现 127）
bash -c '. <build>/generators/conanrun.sh; command -v simstring; simstring -v; echo rc=?'
#   → simstring NOT on PATH / bash: simstring: command not found / rc=127
```

## 根因（conan 源码一行定死）

`conan/tools/env/virtualrunenv.py`：

```python
for require, dep in list(host_req.items()) + list(test_req.items()):
    if dep.runenv_info:
        self._runenv.compose_env(dep.runenv_info)
    if require.run:        # ← 只有 run=True 的依赖才走下面这步
        self._runenv.compose_env(runenv_from_cpp_info(dep, _os))   # 内含 _prepend_path("PATH", cpp_info.bindirs)
```

requires 边的 `run` 由被依赖包 **package_type** 推导：application/shared →
`run=True`；**header-library（与静态库）→ `run=False`** ⇒ `cpp_info.bindirs`
被短路。**机制指纹**：生成的 `conanrunenv-<cfg>-<arch>.sh` 里 `for v in`
变量列表为空（连 profile 没给 runenv 时一个变量都没有），source 后 PATH 无包
目录——而 `package_info()` 里明明写了 `bindirs = ["bin"]`，PF8/L0k 也照常
认 CLI（两闸看 conandata/文本，与 runenv 无关），于是"三处都说有 bin、
PATH 里就是没有"。

对照实验：同仓 `package_type="application"` 的 aa3d，test.sh 里裸调 `aa3d`
过 CI——`run=True` ⇒ bindirs 进 PATH，同机制反向成立。

## 方案

**首选（裁决采信，abiword-plugin-* 族同型）**：test() 显式传 bin 目录作 `$1`：

```python
bindir = os.path.join(self.dependencies["simstring"].package_folder, "bin")
self.run(f'"{bash}" "{script}" "{bindir}"', env="conanrun")
```

```bash
BIN_DIR="${1:?usage: test.sh <package-bin-dir>}"   # 缺参早失败，不静默降级
SIM="$BIN_DIR/simstring"
... "$SIM" -v ...
```

优点：不动 package_type、不依赖 runenv 规则、缺参即报错；MANIFEST.yml 的
`command:` 同步为 `bash test.sh <package-bin-dir>`。

**备选（否决留档）**：`package_type="application"` 让 `run=True`（aa3d 形态）
——头文件库标 application 属**表意失真**，对下游诚实性有害、审视角大概率挑，
仅适用于"本质是工具、头文件附带"的包（simstring 任务裁决否决本包采用）。

## 影响面

- 一切 header-library/static 等 `run=False` 类型却 install 了可执行文件的
  包的 test_package；CI 侧若按裸命令名做 smoke（G4/L2 类）同样会踩。
- 排查口诀：**包内实物在 + 直跑 rc=0 + `for v in` 空表 = run=False 短路**，
  与"打包缺件"“装载器缺库”彻底区分开（后两者分别表现为目录里没有该文件、
  直跑即报 loader 错误）。
