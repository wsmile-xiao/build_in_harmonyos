# E569 — 消费者配方 build() 未注入依赖运行库路径：in-tree 测试程序加载共享依赖失败

- **ID**: E569（草稿）
- **触发**: `conan create`（配方 `build()` 内执行 `make check`）
- **严重度**: medium
- **分类**: testing / dependency-library / shared-linking / environment
- **出处**: libosmocore/1.11.0 适配（PR #9889），2026-09-14

## 现象

`conan create` 的构建期测试阶段（`make check`）出现**只有 1 项失败**且失败原因是共享库加载：

```
51. testsuite.at:319: testing sim ...
.../tests/sim/sim_test: Error loading shared library libpcsclite.so.1: No such file or directory (needed by .../src/sim/.libs/libosmosim.so.22.1.0)
ERROR: 88 tests were run, 1 failed unexpectedly.
```

`libosmosim.so` 由 pcsc-lite 支持（`--enable-pcsc`），运行时需要 `libpcsclite.so.1`；该库是 conan 依赖（`pcsc-lite/2.4.0`），位于 conan 包目录，**不在任何全局搜索路径上**，而 `conan create` 构建期只自动应用工具链（build）环境，不包含宿主依赖的运行库路径。

## 根因

- conan 构建期自动应用的只有 `conanbuild`/工具链环境（CC、CFLAGS 等）；
- in-tree 测试程序运行期需要宿主依赖的 **共享库**（本例 pcsc-lite），而依赖的 lib 目录既不在 `/usr/lib` 也不在产物 RPATH 里；
- 本地开发机常见被泄漏的 `LD_LIBRARY_PATH`/`CPPFLAGS`/`LDFLAGS` 掩盖 → 本地绿、CI 红。

## 修法（首选，已在本包配方落地）

```python
from conan.tools.env import VirtualRunEnv

    def build(self):
        apply_conandata_patches(self)
        env = VirtualRunEnv(self).environment()
        with env.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            autotools.make(target="check")   # 必须在 with 块内
```

要点：
1. `make check` 必须也在 `with` 块内——否则测试程序仍找不到库；
2. 不要用 `-Wl,-rpath,<构建机绝对路径>`（pre-scan 反对 build-machine rpath，产物跨机不一致）；
3. 不要依赖外部 `LD_LIBRARY_PATH`（CI 干净环境没有，本包首轮 CI 即因此暴露）。

## 验证

```bash
LD_LIBRARY_PATH=<pcsc-lite pkg>/lib:<build>/src/*/.libs ./tests/sim/sim_test ; echo $?
# =0  → 库路径是唯一缺口
```

同一二进制不带该变量时 `RC!=0`（报 `Error loading shared library`），带后 `RC=0`，即证明修法对准根因。

## 关联

- E568（静态依赖双实例）：同一多 DSO 结构下的另一种依赖库问题；
- 反模式来源：本地 ambient env（`CPPFLAGS`/`LDFLAGS`/`LD_LIBRARY_PATH`）必须在 **scrubbed 环境**下复现 CI 才能暴露。
