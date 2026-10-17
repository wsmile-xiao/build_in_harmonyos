# DRAFT-qqwing-1.3.4-conanbuild-recursive-source-printenv-e2big：Environment.save_script("conanbuild") 与 AutotoolsToolchain 聚合产生递归 source，printenv Argument list too long

> Contributor: qqwing-1.3.4 适配 | Status: Draft | Updated: 2026-09-20
> Source: archives/q/qqwing/1.3.4

## 现象

qqwing 1.3.4 在 OHOS 真机 shadow CI 上，configure 已跑完（编译器检测、头文件、config.status 都通过），
但进入 make 阶段时，stdout 里反复刷出数十次：

```
/system/bin/sh: .../build-release/conan/conanautotoolstoolchain.sh[13]: /system/bin/printenv: Argument list too long
...
make: *** No targets specified and no makefile found.  Stop.
```

## 根因

配方 `generate()` 里先 `AutotoolsToolchain(self).generate()`，又用
`Environment().vars(self).save_script("conanbuild")` 追加 `LD/AR/RANLIB`。Conan 聚合同名
conanbuild 脚本时，生成的 `conanbuild.sh` 变成了「递归 source 自身」：

```sh
. ".../conanautotoolstoolchain.sh" && . ".../conanbuild.sh" && . ".../conanbuildenv-release-armv8.sh"
```

第二个 `. conanbuild.sh` 又 source 自己 → 死循环。每次递归都执行
`conanautotoolstoolchain.sh` / `conanbuildenv-*.sh` 里的 `value=$(printenv $v)` 与
`export ...`，环境变量无限累积，最终 exec `printenv` 时环境总量超过 OHOS 的 ARG_MAX，
报 `Argument list too long`（E2BIG）。环境 setup 因此失败，make 找不到 configure 生成的 Makefile。

## 边界

- 仅「AutotoolsToolchain + Environment.save_script("conanbuild")」同名聚合时命中。
- 与 mydumper/dejagnu 的 save_script clobber 同根因但表现不同：那里是覆盖 → SIGSEGV，
  这里是递归 source → E2BIG；诊断时按实际现象区分。

## 方案（最小修复）

不用 `save_script("conanbuild")` 追加变量，改为在命令串前直接 export 完整路径（仅单条命令内生效）：

```python
def _toolchain_prefix(self):
    if self.settings.os == "OHOS":
        return ("export LD=/data/service/hnp/bin/ld; "
                "export AR=/data/service/hnp/bin/ar; "
                "export RANLIB=/data/service/hnp/bin/ranlib; ")
    return ""

def build(self):
    ...
    ld = self._toolchain_prefix()
    self.run(f'{ld}make -j1', env="conanbuild", cwd=self.source_folder)
```

- 回退：若必须用 `Environment`，用非 `conanbuild` 的自定义脚本名（如 `save_script("qqwing_buildenv")`），
  再在命令里显式 source，避免同名聚合递归。

## 验证

- 修前：`printenv: Argument list too long` 刷屏 → make 找不到 Makefile（exit 2）。
- 修后：命令内 export LD/AR/RANLIB，configure + make + make install + test_package 全绿（exit 0）。

## 查重结论

- mydumper（DRAFT-mydumper-mysql-stub.kv）已记「save_script("conanbuild") 覆盖聚合环境导致
  self.run SIGSEGV」；dejagnu 已记「用自定义名避免 clobber」。
- 本条为同一根因的**新表现**（递归 source → 死循环 → printenv E2BIG），并给出「命令内 export」
  的最简规避，属补充而非重复。
- E338 覆盖 autotools 的 ar/ranlib 缺失与 config.status mktemp 权限，不含本递归 source 现象。
