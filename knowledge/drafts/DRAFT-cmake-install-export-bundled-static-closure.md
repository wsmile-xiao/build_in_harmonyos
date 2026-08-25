# DRAFT：CMake install(EXPORT) 的 bundled/private 静态依赖导出闭包

> Status: Draft | Updated: 2026-08-24
> Source event: AvogadroLibs 2.0.0 on OHOS aarch64
> Candidate evidence: final consolidated provenance / commit `consolidation OID may change; tree is authoritative` / tree `38f9a2155c3e012dc9d203b61b03e68230ddcb48` / base `250c1906b6fb844d1969e4dbd7c4f714014f4372`

## Provenance refresh

This draft's final provenance is bound to the authoritative tree/base pair above. A later consolidation may change only the commit OID; that OID-only change does not require another provenance refresh. The engineering content is unchanged.

## 严格适用边界

本草稿仅适用于以下条件同时成立的 CMake 安装导出故障：

1. 一个将被安装、被 `install(EXPORT ...)` 导出的静态目标，在其实际链接接口闭包中引用 bundled/private 静态目标；
2. CMake 日志明确报告该依赖目标“不在任何 export set”或语义等价错误；
3. 下游需要通过生成的 `*Targets.cmake` / package config 解析并链接该闭包。

不能因为源码树中存在 vendored 静态库就将其全部导出。如果依赖本应真正私有、并不应出现在导出接口，优先修正 `target_link_libraries` 的 `PUBLIC` / `PRIVATE` / `INTERFACE` 可见性，而不是扩大公共导出面。

## 触发

AvogadroLibs 2.0.0 的前一候选通过权威入口 `ci/conan/build_and_test.sh` 运行 `conan create` 时，在 CMake configure 阶段失败。设备报告记录：导出集中的 `IO` 目标需要 `struct` 和 `pugixml`，但二者不在任何 export set。

证据：

- `reports/builder/authoritative-ci.md`
- 上游版本：tag `2.0.0`，commit `d41dbf36dd92fcf275f25bb5f3ad4063a838ed3a`

## 根因

`install(EXPORT ...)` 生成的导出元数据必须能解析被导出目标的实际链接接口闭包。`IO` 引用了 bundled 静态目标 `struct`、`pugixml`，但这两个目标没有加入 `AvogadroLibsTargets`。因此 CMake 无法生成自洽的安装导出。

这里的“private”只表示项目内部 bundled target，不表示它一定不会出现在导出接口。是否需要导出必须由 target graph 和链接可见性决定。

## 修复模式

1. 固定源码版本并从原始日志提取目标名、export set 名和失败原文。
2. 检查 `target_link_libraries` 的可见性和生成导出接口：
   - 若依赖本应不暴露，优先修正链接可见性；
   - 若消费者确实需要解析该 target，将其加入同一 export set。
3. 对需要闭合的依赖使用项目实际目标名补充：

```cmake
install(TARGETS <required-bundled-targets>
        EXPORT <same-export-set>
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin)
```

4. 同步安装真实 consumer 所需的 archive、headers、config/targets 元数据。不要只消除 configure 错误，也不要照搬 Avogadro 的单点 marker 文本编辑作为通用方案。

Avogadro 候选在唯一 `install(EXPORT "AvogadroLibsTargets")` 前守卫式加入 `struct`、`pugixml`，并安装相应 archive。该实现是本库的受控落地方式，不是通用自动修复脚本。

## 安装验证

修复后的权威 CI 明确确认安装产生：

- `libstruct.a`
- `libpugixml.a`
- `AvogadroLibsTargets.cmake`

只生成 `*Targets.cmake` 或只让 configure 通过都不足以证明修复成立；导出元数据引用的制品必须实际装包。

## 真实 consumer 验证

最终 `test_package` 通过 Conan 生成的 package config 执行 `find_package(AvogadroLibs REQUIRED)`，链接 `Avogadro::Core` 与 `Avogadro::IO`。除 CJSON 序列化外，它还调用 pugixml-backed `CmlFormat::write`，并调用 struct-backed `DcdFormat::read` 处理畸形输入，使最终可执行文件必须解析 `libpugixml.a` 与 `libstruct.a` 的静态闭包，然后完成 configure、build、link、run。设备输出为 `avogadrolibs consumer test passed`。

证据：`reports/builder/authoritative-ci-final.md`。该报告同时限定 upstream CTest 因 `ENABLE_TESTING=OFF` 未运行，不能将其表述为 PASS。

## 相近跨库案例：flann / lz4_vendored

`archives/f/flann/1.9.2/manifest.yaml` 与 `notes.md` 记录了相同机制的项目先例：静态目标 `flann_cpp_s` / `flann_s` 的链接接口引用 `lz4_vendored`，导致 `install(EXPORT)` 报依赖不在导出集。修复将 `lz4_vendored` 加入 `flann-targets`，同时安装 `liblz4_vendored.a` 和消费者需要的头文件。

该先例证明问题并非 Avogadro 专属；Avogadro 的 `struct` / `pugixml` 案例又补充了另一库及 Conan/CMakeDeps 下游消费链路。本草稿是知识扩展，不宣称现象首次出现。

## 禁止与反例

- 禁止无条件导出全部 vendored targets；这会泄漏不受支持的内部接口。
- 若依赖本应真正私有且不进入消费者接口，优先修正可见性。
- 禁止只检查 configure；必须检查 archive/config 安装以及真实 consumer link/run。
- 禁止复制 Avogadro 的目标名、安装目录、marker 编辑或 flann 的目标名作为通用实现。
- 本草稿不覆盖 `patch_ng` 的 `a/`、`b/` 路径及 strip-level 解析。该主题已有 `archives/m/minisign/0.12/notes.md` 与 `knowledge/drafts/E334-draft-MLTN.kv/.md`，不得重复创建知识项。
