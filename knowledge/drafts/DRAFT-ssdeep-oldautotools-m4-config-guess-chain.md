# DRAFT: 2012 老 autotools tarball 缺 m4/ 宏目录 + 旧版 config.guess 的 OHOS Conan 适配四步链

> 草稿条目（与 `DRAFT-ssdeep-oldautotools-m4-config-guess-chain.kv` 同 stem 配套）。
> 状态：DRAFT — 待人工/AI 审核提升为 E-条目。

## 问题现象（ssdeep 2.8 实测）

```
initializing: configure: error: cannot guess build type; you must specify one
# config.guess timestamp = 2005-12-13，uname -s = HarmonyOS 无法识别

make: 触发 automake maintainer 重生成链失败：
  aclocal-1.12: inaccessible or not found
  automake-1.12: inaccessible or not found
  m4:aclocal.m4:998: cannot open `m4/libtool.m4': No such file or directory
  autom4te: error: m4 failed with exit status: 1
```

## 根因

2012 年代 autotools 工程 tarball 的三个形态特征同时命中：

1. **缺 m4/ 宏目录**：tarball 打包了预生成的 `configure`/`Makefile.in`/`aclocal.m4`，
   但 `aclocal.m4` 内含 `m4_include(m4/libtool.m4)` 等引用，m4/ 目录未随包发布；
2. **config.guess 过旧**：2005 版无 `__OHOS__` 分支，`uname -s = HarmonyOS` 无法匹配；
3. **CI/本地无老版本工具**：`aclocal-1.12`/`automake-1.12` 不存在，一旦 make
   因 maintainer 规则触发重生成链（aclocal.m4 的依赖缺失会"永不过期"），必然失败。

E007/E160 的补丁方案（`patch-autotools-ohos.pl`、sed 加分支）适用对象是新式
config.guess（有统一 `GUESS=` 输出结构）；对 2005 版脚本与缺 m4/ 目录的组合不适用。

## 方案（4 步链）

```bash
# 1. vendored 替换 config.guess/config.sub（≥2023 版，含 __OHOS__）
#    patches/autotools/config.guess + config.sub，source() 复制进源码树
# 2. libtoolize 补齐 m4/ 宏文件（vendored 进 patches/autotools/m4/）
libtoolize --copy --force
# 3. 重建构建系统（旧宏仅废弃警告，可成功）
autoreconf -fi
# 4. Conan build() 阻止 maintainer 重生成：autotools 依赖文件时间戳设为过去，
#    configure 保持最新（参照 babeltrace 1.5.11）
```

关键配方导出要点：`export_sources()` 必须 `copy(self, "patches/*", ...)`，
否则 conan-verify 用 cache 内 source 时 `source()` 复制不到 vendored 文件，
G2 首跑必失败（ssdeep 实测：G2 FAIL → 修复 export_sources → G0-G4 全 PASS）。

## 验证（ssdeep 2.8）

- 本地：`./configure && make -j1 && make install` 通过，CLI 实际运行产出 fuzzy hash；
- Conan：`conan create` G2 通过，test_package 1/1 Passed；finish W3 `.ci-result.json` exit_code=0；
- 环境：OHOS aarch64，clang 15，`config.guess` 2023-08-22 / `config.sub` 2023-09-19。

## 适用边界 / 反例

| 场景 | 适用性 |
|------|--------|
| tarball 含预生成 configure 但缺 m4/ | ✅ 必须 libtoolize 补 m4/（否则重生成链必炸） |
| tarball 已含 m4/ 宏文件 | ⏭ 不需要步 2（libtoolize）；步 1/4 视 config.guess 年代 |
| 源码仓库 git tag（含 auto* 生成文件与 m4/） | ⏭ 不需要 autoreconf 重建，注意 ci 环境下时间戳 |
| config.guess 已是 2023+（含 __OHOS__） | ⏭ 步 1 跳过 |
| 工程用 autoreconf 驱动的 autogen.sh | ⚠️ 需先确保 aclocal/automake 版本可用，不能照搬"vendored 替换" |

## 关系

- similar_to: E007, E160（config.guess 不认识 OHOS）、E041（automake 重生成）、
  E514/E521（libtoolize/ltmain.sh）、DRAFT-6048（babeltrace timestamps 阻止重生成）、
  DRAFT-E564（旧式 config.guess 换锚点）
- 差异：本条目首次把"缺 m4/ 目录 → libtoolize 补齐 + autoreconf 重建 + vendored 替换
  + timestamp 阻止重生成"组合为四步链，并显式记录 export_sources 导出要点。

## 相关知识来源

- 三方库：ssdeep 2.8（archives/s/ssdeep/2.8，本次 PR 同批次）
- 参照配方：archives/b/babeltrace/1.5.11/conanfile.py（timestamps 处理）