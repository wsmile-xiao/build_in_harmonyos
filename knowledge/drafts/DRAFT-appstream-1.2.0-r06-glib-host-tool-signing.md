# DRAFT-appstream-1.2.0-r06-glib-host-tool-signing — 构建期 exec 依赖包内 ELF 宿主工具：消费者侧复制→去旧签→自签→wrapper

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: high (1) | **Category**: conan / signing / codesign / host-tool / build
> **Audience**: 构建期 exec 依赖包 bin ELF 工具的 Conan 库（glib/meson 资源生成等）

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R06）：CI 干净重建（build 目录 appstcfaa8de09d1c4）
  ```
  [code=126] Generating src/as-resources.c / asw-resources.c / ..._h
  build-release/glib-tools/glib-compile-resources[3]:
    .../.cache/conan2/p/glibcad7259522c98/p/bin/glib-compile-resources: Operation not permitted
  ```

## 症状（symptom）

- glib 包内宿主 ELF（glib-compile-resources）被内核拒绝加载：EPERM，ninja code=126；
  直接 `--version` 同样报 `Operation not permitted`（非缺库，LD_LIBRARY_PATH 已配）。

## 机制（root cause）

OHOS 内核只加载含**有效 `.codesign` 签名段**的 ELF。conan 依赖包 `bin/` 下的宿主 ELF
工具（glib-compile-resources、glib-compile-schemas）在干净环境签名缺失或失效；R03
wrapper 只 `export LD_LIBRARY_PATH` + exec 原二进制，从不签名——CI 干净重建必然复现
（R05 本地成功依赖既有构建产物/缓存）。

## 修复（fix）

R06 conanfile.py `generate()`：
1. 把依赖包 `bin/glib-compile-resources` 复制到构建私有目录 `glib-tools/*.bin`；
2. 对 ELF（魔数 `\x7fELF`）：`llvm-objcopy --remove-section .codesign` 清旧签名残留 →
   `binary-sign-tool sign -inFile X -outFile X -selfSign 1` 自签 → `chmod 755`；
3. wrapper 脚本 `export LD_LIBRARY_PATH=<glib>/lib` 后 `exec` **已签名副本**；
4. python 脚本（glib-mkenums/genmarshal/gdbus-codegen）直用，不签名。

## 验证（verification）

- 全新 build 目录 appstf060205c24243：conan create 全流程 `[1/288]→[288/288]`
  exit_code=0，**0 命中 `Operation not permitted`/`code=126`**；
- `glib-compile-resources.bin` 自签后 `.codesign` 段就位，wrapper 指向签名副本；
- 上游测试 14/14（as-test_compose 18/18 含 MediaImage/MediaFont）。

## 适用边界 / 反例

- 适用：构建期被 exec 的依赖包 ELF 宿主工具（glib 资源/枚举生成器等），需消费者侧签名；
- 反例：post-install 修改自身产物 ELF（E077 场景，四步流程直接在安装目录执行）；
  python/perl 脚本工具无需签名。

## 关系

- 查重：E077（ELF 必须含有效 .codesign 才能被内核加载 + post-install 四步签名流程）
  覆盖自身产物 ELF 修改；本候选是**构建期 exec 依赖包宿主工具 + 消费者侧复制签名**——
  边界不同（trigger: build-host-tool vs post-install；solution: 构建私有目录副本 vs
  安装目录原地）。
- similar_to: E077；caused_by: glib 包宿主 ELF 签名缺口（依赖包现状）；
  prerequisite_of: []; conflicts_with: []

## 证据

- 配方：archives/a/appstream/1.2.0/conanfile.py（generate() 签名逻辑）
- 重建日志：/storage/Users/currentUser/tmp/builds/r06-conan-create1.log
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 20