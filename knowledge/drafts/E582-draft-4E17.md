# E582 — CI 任务域 hmmac 标签拒绝 dlopen 用户目录 .so（与 ELF 签名无关）：预编译 wheel 自检回退为静态 ELF/.codesign 校验

## 错误特征

封装预编译 wheel（或任何预编译二进制）的 Python 配方，在**真机 / 设备侧**本地一切正常，
但在 **CI worker / 干净沙箱**内 import 即失败：

```
ImportError: Error loading shared library
  /.../numpy/_core/_multiarray_umath.cpython-312-aarch64-linux-ohos.so: Permission denied
```

注意特征：报的是 **Permission denied（EACCES）**，不是 `cannot open shared object file`
（缺文件）、也不是 `undefined symbol`（缺符号）。手工测试 `ImportError` 指向的第一条路径通常是
**依赖包**（如 numpy）而非主包本身，容易误判为依赖问题而反复在依赖版本上打转。

> ⚠️ 只认加载器的 **errno 后缀**（`: Permission denied` / `: EACCES`），**绝不以裸
> `Error loading shared library` 前缀**匹配——真正「缺库」时动态加载器同样打印该前缀
> （`: No such file or directory`），按前缀匹配会把缺依赖误判为本问题而掩盖真实缺陷。

## 触发条件

- 构建系统: Python / pip（封装预编译 wheel，不做源码编译）
- 阶段: build() 内的包内自检 / test_package / 消费者运行时
- 环境: CI worker 等沙箱；真机 / 交互设备域复现不出来（见根因）

## 根因分析

**CI worker 的任务域安全标签（hmmac）按文件所在路径授权加载，与 ELF 代码签名无关**
（知识条目 **E212** / **E502**）：

- 只有 `hnp_file` 标签（`/data/service/hnp/` 下，经 `hmmac=inherit_parent` 继承）的 `.so`
  允许被 `dlopen`；
- 用户可写目录（`/storage/Users` 的 hmdfs 标签、`/data/storage/el2/base` 等）下的**任何**
  `.so` 一律被拒，报 EACCES，无论其是否携带有效的 `.codesign` 签名段。

因此这是**路径 / 标签策略**：`.so` 已正确代码签名、真机（HNP 进程域）加载正常，CI 侧仍报
`Error loading shared library <path>.so: Permission denied`。**重新签名无法修复 CI 失败。**

> **真机（HNP worker）实测补充**：把已签名 ELF 拷到新路径后 `dlopen` 报 `<path>.so: Permission denied`；
> 用 `/data/service/hnp/bin/binary-sign-tool sign -inFile F -outFile F.signed -selfSign 1` 重签后
> 恢复可加载（普通拷贝 = Permission denied，拷贝重签 = load OK）。可见 wheel 解包出的副本**仍需重签名**，
> 但重签名**绕不过** E212 的路径 / 标签策略。

真机 / 交互设备域较宽松，CI worker 任务域较严格，于是出现「本地/真机全绿、CI 必红」的偏差——
本地 dlopen 成功不能迁移到 worker。

> 实测：yt 4.4.2 封装社区源 OHOS 预编译 wheel，真机 `import yt` 正常、全量上游套件
> **792 passed / 97 skipped / 0 failed**；CI 首轮在 `conan-build-test` 步骤失败，日志显示
> import numpy 扩展时 `: Permission denied`（E212，非缺符号/缺文件）。

## 解决方案

### 推荐方案

CI 侧**不再要求真实 dlopen**：配方自检捕获 stderr，命中**加载器措辞 + errno 后缀同行同现**
（如 `Error loading shared library <path>.so: Permission denied`）才判定为 E212，回退到**静态校验**
——对 staging 内每个 `.so` 校验 ELF 魔数与 `.codesign` 段；真实功能证据改由真机 / 本地实测提供。

```python
# 判据：双条件**同行同现**——加载器措辞 + errno 后缀；二者缺一不成立
_LOADER_CONTEXT = (
    "Error loading shared library",    # musl（OHOS/CI 实测）
    "Error relocating",
    "cannot open shared object file",  # glibc
)
_ERRNO_SUFFIXES = (": Permission denied", ": EACCES")

def _is_e212(text):
    for line in str(text).splitlines():
        if any(ctx in line for ctx in _LOADER_CONTEXT) and \
           any(sfx in line for sfx in _ERRNO_SUFFIXES):
            return True
    return False
```

```python
# 静态校验：ELF 魔数 + .codesign 段（工具缺失时退化为纯 Python 字节扫描）
for path in sos:                       # sos = staging 内全部 *.so 与 *.so.*
    with open(path, "rb") as fh:
        assert fh.read(4) == b"\x7fELF", path          # ELF 魔数
    signed = ".codesign" in subprocess.run(
        [objdump, "-h", path], capture_output=True, text=True).stdout
    if not signed:                     # 工具不可用时兜底
        signed = b".codesign" in open(path, "rb").read()
    assert signed, path
```

要点：

- **errno-specific 标记**：只匹配 `: Permission denied` / `: EACCES`；**不能**匹配裸
  `Error loading shared library` 前缀（缺库 ENOENT 共享该前缀，会误判）。
- 静态校验通过则打印 `PASS` 让 `conan create` 成功，并**如实报告**：运行时 `import` 需经 HNP
  安装到真机验证；**任何非 E212 的自检失败仍然抛错**，不放行。
- wheel 解包出的 `.so` **副本仍需重签名**（真机实测：已签名 ELF 换路径后 dlopen 失败、重签后恢复），
  在 `build()` 内归一化之后对 staging 全部 `.so` 执行：先
  `llvm-objcopy --remove-section .codesign` 剥旧段（缺段时非致命），再
  `binary-sign-tool sign -inFile F -outFile F.signed -selfSign 1` 并移回 + `chmod 755`。
- 遍历目录按 `filename.endswith(".so") or ".so." in filename` 匹配，覆盖带版本号的 `.so.x.y`；
  签名工具不存在时（纯 Linux 构建机）跳过并 warn，不要硬失败。
- 必须在**归一化扩展后缀之后**执行——重命名会丢掉 / 错配签名关联。
- 参考实现：`archives/y/yt/4.4.2/conanfile.py`（本次 fix 实际落地处，函数 `_is_e212` /
  `_e212_static_verify` / `_self_check`）；同类先例 `archives/n/numpy/1.26.4/conanfile.py`。
- 数量口径：重签 **115** 个共享对象（日志 `code-signed 115 shared object(s)`）；归一化扩展后缀
  **93** 个（扩展模块数，与 `.so` 总数口径不同）。

### 禁止做法

- ❌ **以裸 `Error loading shared library` 前缀判 E212**：真正缺库（`: No such file or directory`）
  同样带该前缀，会把依赖缺失误判为静态 PASS → 假绿，真实缺陷流入发布。
- ❌ 把 CI 的 EACCES 当成依赖版本冲突，反复升降 numpy/scipy 版本（方向性错误，永远不会收敛）。
- ❌ 把 E212 当作签名问题，企图靠**重签名 / chmod 755** 修复 CI（路径 / 标签策略与签名、权限位无关）。
- ❌ 只在真机侧验证就宣称适配完成（真机域宽松，掩盖 E212，必须按 W3 在干净环境复验）。
- ❌ 删掉 CI 里报错的那个依赖来「绕过」（破坏功能，且其他扩展同样会在运行时崩）。

## 验证

```bash
# 真机 / 设备侧：真实功能证据（CI 侧不做真实 dlopen）
python3 -c "import yt, numpy; print(yt.__version__, numpy.__version__)"
# 预期: 4.4.2 2.2.6
# 真机实测: 上游 pytest 套件 792 passed / 97 skipped / 0 failed；消费者测试 7/7；bin/yt -h rc=0

# CI 侧：E212 静态校验 —— 每个 .so 为合法 ELF 且含 .codesign 段
llvm-objdump -h <lib>.so | grep -i codesign      # 或 llvm-readelf -S <lib>.so | grep -i codesign
# 命中 : Permission denied / : EACCES 即走该回退；未命中任何标记则不得回退
```

## 关联条目

- 根因 / 路径标签策略: **E212**（hmmac 安全标签阻止从用户路径 dlopen `.so`）、
  **E502**（CI worker 拒绝对用户目录 `.so` 的 dlopen/LD_PRELOAD，与 ELF 签名无关）
- 签名段机制: **E077**（post-install 签名，`.codesign` 段）
- CI 环境: **E219**（CI buildenv 下勿将非 HNP python 作为 conan create 硬门禁）
- 同类先例: `archives/n/numpy/1.26.4`（预编译扩展封装 + 签名）、`archives/y/yt/4.4.2`（本次 fix 落地处）
