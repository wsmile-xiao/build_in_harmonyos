# 官方 tag 包无 configure 且 autotools 工具包在 HMDFS 真机不可构建时，改走上游 Makefile.unx

- **草稿 ID**: DRAFT-libisal-2.31.1-autotools-unbuildable-makefile-unx
- **来源**: libisal 2.31.1 HarmonyOS PC 适配（第一版 autotools bootstrap 配方在真机被 tool_requires 构建阻塞，改 Makefile.unx 路线后全绿）
- **分类**: conan / autotools / hmdfs / build-system / makefile-unx
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- 上游 release 只挂 tag 无 dist 资产 → 官方源码包**没有 configure**，常规解法是 `tool_requires automake/autoconf/libtool` 从源码构建工具（zzuf/avimetaedit 在 CI worker 的先例）。
- 但真机（HMDFS）上这条路被三重堵死：
  1. 工具包自身构建第一步 `autotools.configure()` 直接 exec configure → **Error 126 Permission denied**（HMDFS 拒脚本直接执行，chmod 无效）；
  2. automake 构建依赖 conan `perl/5.42.2`，其 **Cwd.so 在 HMDFS 上 dlopen 失败**；
  3. ohpcd 制品仓**无这些工具的预构建二进制**（`conan download automake/1.18:<id>` → not found）。

## 解法：上游 Makefile.unx + make.inc

libisal（isa-l）源码树自带 `Makefile.unx` + `make.inc`：**include 与 autotools 完全相同的各模块 `Makefile.am` 源列表**，按 `host_cpu` 选 aarch64 源（NEON/SVE/C 基础实现全量），`AS=$(CC) -D__ASSEMBLY__` 汇编 .S，支持 `lib`（bin/isa-l.a）、`slib`、`progs`（igzip CLI）、`check`（上游测试）、`install` 目标——是上游维护的正式构建路径，不是旁路 hack。

配方要点（全部真机实证）：

| 要点 | 原因 |
|------|------|
| `arch=aarch64 host_cpu=aarch64` 显式传入 | make.inc 的 `uname` 启发式在 HarmonyOS 上得到 "HarmonyOS" 而非 aarch64 |
| 只传 `CC`/`AR` 命令行变量 | make.inc 的 `CFLAGS = ...` 是普通赋值，命令行传 CFLAGS 会整体覆盖丢 -I/-O2；CC 是 `?=` 且 `AS=$(CC)`、`LINK.o` 同源，传 CC 全规则生效 |
| `TMPDIR` 指向可写目录 | make.inc 的汇编特性/pthread 探测用 mktemp，OHOS /tmp 只读 |
| 打包手动 copy | `install` 目标含 man/symlink 步骤；igzip 产物在 **programs/** 下（bin/ 只有 .o/.a） |
| 无需 -fno-integrated-as | clang 15 集成汇编器实测可编全部 52 个 aarch64 .S（含 .req 别名），frp 机无 GNU as 也全绿 |

```python
def _make_base(self):
    executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    cc = executables.get("c", "clang")
    ar = executables.get("ar", "llvm-ar")
    return (f'make -f Makefile.unx arch=aarch64 host_cpu=aarch64 '
            f'version={self.version} CC="{cc}" AR={ar}')
# build(): make lib progs && make check（上游 16 测试）
```

## 推广

- 判断依据：源码树有 `Makefile.unx`/`Makefile.nmake`/`make.inc`（isa-l/isa-l_crypto 系）或其他 include Makefile.am 片段的手写 makefile → 优先走它，跳过 autotools 工具链自举。
- 若上游无备用构建系统：只能等 ohpcd 发布 autotools 预构建，或在非 HMDFS worker 预构建后上传。
- 相关：HMDFS exec 问题即 cdb/libfec 配方里 `bash "configure"` 绕法的根因；本条是其在 tool_requires 层面的表现（工具包配方无法像自家配方那样改用 bash 调用）。
