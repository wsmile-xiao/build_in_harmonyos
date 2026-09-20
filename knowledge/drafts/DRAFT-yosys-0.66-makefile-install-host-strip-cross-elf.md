# DRAFT-yosys-0.66 — make install 的 $(STRIP) 在交叉构建下解析到宿主 strip

## 使用说明

自带 Makefile 的项目常写 `STRIP ?= strip`。交叉构建时 `make install` 会调用宿主 `strip`，
而宿主 strip 往往无法识别目标的 aarch64-ohos ELF，报 `strip: Unable to recognise the format`，
`make install` 以 `Error 1` 中止（编译、链接其实都已成功）。

处置：从 C 编译器同目录取 `llvm-strip`（OHOS SDK 随 clang 一起提供），传给 install 步骤。

```python
def _strip_cmd(self):
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    cc = compilers.get("c")
    if not cc:
        return ""
    cand = os.path.join(os.path.dirname(cc), "llvm-strip")
    return 'STRIP="%s"' % cand if os.path.isfile(cand) else ""

self.run('%s make install PREFIX=%s ...' % (self._strip_cmd(), self.package_folder), env="conanbuild")
```

## 适用范围

- 构建系统：自带 Makefile，且 install 目标用 `$(STRIP)`（`STRIP ?= strip`）
- 阶段：installation（编译/链接已通过）
- 交叉构建（host 与 build 架构不同）；native 构建默认值可用，不受影响
- 不适用：install 不 strip 的项目；或构建机已装目标架构 strip

## 输入输出定义

- 输入：`tools.build:compiler_executables.c`（用于推导同目录的 `llvm-strip`）
- 输出：`make install` 环境前缀中的 `STRIP=<abs>/llvm-strip`
- 成功信号：install 完成、`bin/` 下二进制被 `-S` 处理（实测 306MB → 26MB）

## 示例

```
$ make install PREFIX=/tmp/inst ENABLE_ABC=1 ABCEXTERNAL=... DISABLE_SPAWN=0
cp yosys yosys-config ... /tmp/inst/bin
if [ -n "strip" ]; then strip -S /tmp/inst/bin/yosys; fi
strip: Unable to recognise the format of the input file `/tmp/inst/bin/yosys'
make: *** [Makefile:974: install] Error 1
```

修复后：

```
if [ -n "/home/.../llvm/bin/llvm-strip" ]; then .../llvm/bin/llvm-strip -S /tmp/inst/bin/yosys; fi
$ du -sh /tmp/inst
37M     /tmp/inst        # RC=0
```

## 设备侧连带后果：strip 会作废 `.codesign`（必须重签）

在**鸿蒙设备**上，交叉构建期的「宿主 strip 读不了 ELF」不会出现（设备 strip 就是目标架构的），
但同一个 `make install` 里的 strip 会引发**另一个**问题：OHOS 的 clang/lld 在**链接期自动自签**
一个 `.codesign` 段，任何后续修改 ELF 内容的动作（`strip`/`objcopy`/`patchelf`）都会使签名失效，
内核随后拒绝加载，真机执行报 `Operation not permitted`（EXIT=126）。

实测：CI 构建 #50968 在 `conan-build-test` 失败，日志为

```
yosys/0.66 (test package): RUN: /data/service/hnp/bin/bash -c './test_yosys'
FAIL: non-zero exit from: yosys -V 2>&1
--- output tail ---
sh: /storage/Users/.../conan2/p/b/yosys5d8e4be699acf/p/bin/yosys: Operation not permitted
```

而同一日志中 `make install` 确实执行了：

```
if [ -n "/data/service/hnp/bin/llvm-strip" ]; then /data/service/hnp/bin/llvm-strip -S .../bin/yosys; fi
```

处置（E077 四步流程，设备上生效、宿主上自动 no-op）：

```python
def _resign(self, path):
    sign_tool = "/data/service/hnp/bin/binary-sign-tool"
    objcopy = "/data/service/hnp/bin/llvm-objcopy"
    if self.settings.os != "OHOS" or not os.path.exists(sign_tool):
        return
    tmp = path + ".signed"
    self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, path), quiet=True)
    self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign_tool, path, tmp), quiet=True)
    os.replace(tmp, path)
    os.chmod(path, 0o755)
```

在 `package()` 的 `make install` 之后，对 `bin/` 下每个 ELF（按魔数 `\x7fELF` 判断，跳过 shell/python 包装脚本）调用一次。

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `DRAFT-binn-3.0-raw-makefile-strip-musl-symbol` | 都涉及 raw Makefile 里的 `$(STRIP)` | 那条是「用 llvm-strip 处理 .so 后 musl 无法解析导出符号」；本条是「宿主 strip 读不了目标 ELF，install 直接失败」，处置是用目标架构 llvm-strip |
| `DRAFT-ohos-elf-skip-strip-codesign` | 都关于 strip 失败 | 那条是 OHOS 上 `strip→.codesign EPERM` 的替代路径；本条是交叉构建下工具选错 |

## 验证证据

```
$ grep -n 'STRIP' Makefile | head -2
126:STRIP ?= strip

$ strip -S /home/qianxia/.conan2/p/b/yosys.../p/bin/yosys
strip: Unable to recognise the format of the input file `.../bin/yosys'   # RC=1

$ /home/.../llvm/bin/llvm-strip -S .../bin/yosys && ls -l .../bin/yosys
-rwxr-xr-x 1 qianxia qianxia 26571224 .../bin/yosys    # 306487664 -> 26571224，RC=0

$ STRIP=.../llvm-strip make install PREFIX=/tmp/yosys-inst ...
INSTALL_RC=0 ; du -sh /tmp/yosys-inst = 37M
```

- 退出码：修复前 install=1（033-local-create.log）；修复后 install=0（隔离复验，命令与输出见上）
- 日志绝对路径：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`（失败）、`034-local-create.log`（同一 recipe 增量复验，`yosys/0.66: Already installed!` + test_package 两条 PASS）
- 上游任务：PR #11115
