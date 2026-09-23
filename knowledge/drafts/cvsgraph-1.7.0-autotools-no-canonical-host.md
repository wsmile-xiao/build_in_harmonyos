# cvsgraph 1.7.0 — 无 AC_CANONICAL_HOST 老 autotools：configure 会真实运行 conftest

## 现象

老 autotools 包（cvsgraph 1.7.0，autoconf 2.61）在 OHOS 上：

- tarball 里**没有** `config.guess`/`config.sub`，想打补丁无文件可打
- configure 报 `checking whether the C compiler works... configure: error:
  cannot run C compiled programs. If you meant to cross compile, use '--host'.`
- **两个触发场景**：①真机上共享依赖无运行期库路径（conftest 链了
  `-lgd` 但 `Error loading shared library libgd.so.3`）；②CI worker 沙箱
  禁止 exec conftest 二进制（cadaver #30663 实证，症状逐字相同）

## 根因

1. `configure.in` 从未调用 `AC_CANONICAL_HOST`/`AC_CANONICAL_SYSTEM`：
   无 `$host` 三元组语义，交叉编译只能靠 CC/CFLAGS 环境变量
   （Conan AutotoolsToolchain 的默认注入路径）。
2. `cross_compiling=no` 硬编码 → configure **真实运行** conftest：
   "checking whether the C compiler works" 直接 exec `./a.out`，
   AC_CHECK_FUNCS 也是运行检测。
3. AutotoolsDeps 把共享依赖注入 LIBS（`-lgd -lfreetype ...`）后，
   conftest 的 DT_NEEDED 含 `libgd.so.3`；构建环境只有链接期 `-L`，
   没有运行期库路径 → 加载失败（场景①）。
4. CI worker 沙箱禁止运行新生成的可执行文件 → 场景②，注入库路径
   也救不了（PR #10072 构建 #47863 实证：LD_LIBRARY_PATH 已注入仍失败）。

## 修复（cvsgraph 真机 + CI 实证，2026-09-15）

**标准解法：configure 加 `--host=aarch64-linux-ohos`（不带 `--build`）**

autoconf 2.5x 即使没有 AC_CANONICAL_HOST，`--host` 也走官方 cross 触发器
（configure 内 `host_alias` 非空且 `build_alias` 为空 → `cross_compiling=maybe`
+ 一条 WARNING）。此后 works-check：

- conftest 可运行（真机原生构建）→ 通过，`cross_compiling=no`，全部
  真实运行检测保留
- 被沙箱拦截（CI worker）→ **自动降级** `cross_compiling=yes` 继续，
  链接期 `AC_CHECK_LIB(gd/...)` 探测不受影响

CC 由工具链环境显式指定（`checking for gcc... /data/service/hnp/bin/clang`），
`ac_tool_prefix` 前缀查找不参与；cross 模式下 memset/strdup/strtol 无
HAVE_ 宏但 cvsgraph 源码零守卫（libc 直接提供），无害。

**辅助（场景①）：conftest 运行期库路径，内联追加注入**

```
LD_LIBRARY_PATH="<deps -L dirs>:$LD_LIBRARY_PATH" \
  CONFIG_SHELL=/system/bin/sh /system/bin/sh configure --prefix=/ --host=aarch64-linux-ohos
```

要点：
- 提取正则用 `-L([^\s"]+)`——`\S+` 会把 shell 文件行尾引号吞进路径，
  导致 `/system/bin/sh: no closing quote`
- **不能**用 `Environment().define("LD_LIBRARY_PATH", ...)`：
  `self.run(..., env="conanbuild")` 会 source `conanbuildenv-*.sh`，
  其 `export LD_LIBRARY_PATH=...` 覆盖外层值（真机实测）
- `ac_cv_prog_cc_works=yes` cache 变量在 autoconf 2.61 生成物上**无效**
  （works 检查不走该缓存变量；cadaver #6257 的做法适用于 2.6x+ 生成物）
- 误判警示：真机场景此错不是 XPM 签名也不是 noexec——先看 `config.log`
  中的真实失败行（`Error loading shared library libgd.so.3`）；但 CI
  worker 场景确实可能是沙箱禁 exec（注入库路径仍失败时按 #30663 处理）
- LD_LIBRARY_PATH 用**追加**语义（`:$LD_LIBRARY_PATH`）：CI 的 lld 依赖
  profile 注入的 llvm/lib 下 libxml2.so.16，替换语义会在部分 worker 上
  弄挂链接（ohos-ci-environment-issues）
- 真机（原生构建）+ 注入路径后，works-check 与 AC_CHECK_FUNCS 全部真实
  通过；CI 上由 --host 的 maybe 降级兜底——两套环境一个配方通吃

## 关联

- E386（能力探针选 shell）——本项目同日实证的另一坑
- cvsgraph 配方：archives/c/cvsgraph/1.7.0/conanfile.py
