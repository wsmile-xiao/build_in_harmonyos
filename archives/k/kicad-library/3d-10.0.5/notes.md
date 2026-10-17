# kicad-library 3d-10.0.5 适配笔记

## 上游与产物

- 使用 KiCad 官方 `kicad-packages3D` 项目 **tag 10.0.5**（2026-07-20 打标，commit `67538dca1b8583dec9bd2a45d4eeced6fa287923`）的 3D 模型数据。
- 源归档取 Ubuntu 26.04 / Debian 的 `kicad-packages3d` **10.0.5-1** 官方再打包源码归档（pristine orig tarball，`.tar.xz`，313174800 字节），由 USTC / 阿里云 Ubuntu 软件源镜像提供（conandata.yml 双 URL 回退）。
  - 选源原因：CI 网络无法直连 gitlab.com（connect timeout，2026-09-24 四次构建实测）；GitHub 官方镜像（github.com/KiCad/kicad-packages3D）停更于 5.1.7，无 10.x 内容；Debian/Ubuntu 官方再打包归档是最可信的第三方字节冻结来源。
- SHA-256 `318d41cfe816fc13686ec6964040c3de888b1f6ab357a3e9f98b119c7ba47e4c`，与 Ubuntu 软件源 `kicad-packages3d_10.0.5-1.dsc`（PGP 签名发布）的 `Checksums-Sha256` 一致；本地下载实测 313174800 字节，校验完全一致。
- 归档内容与上游 tag 10.0.5 的 GitLab 归档逐文件比对：105 个 `.3dshapes` 目录、7245 个 `.step` 文件、0 个 `.wrl` 完全一致；唯一差异是 Debian 再打包移除了 1 个不参与安装的 FreeCAD 源文件（`Button_Switch_SMD.3dshapes/SW_SPST_FSMSM.fcstd`）。归档顶层目录为 Ubuntu 打包临时名，`strip_root=True` 已处理。
- 上游根目录包含 **105 个 `*.3dshapes` 模型库目录**，共 **7245 个 `*.step` 模型文件**；KiCad 10 已移除 VRML 模型（0 个 `.wrl`）。
- 上游 `CMakeLists.txt` 使用 `project(kicad-packages3d NONE)`，`install(DIRECTORY ... FILES_MATCHING PATTERN "*.step")` 将模型安装到 `share/kicad/3dmodels`（`KICAD_PACKAGES_3D = ${KICAD_DATA}/3dmodels`），CREDITS.md 等说明文件不进入安装树。
- `LICENSE.md` 为 CC-BY-SA-4.0，本包原样保留到 `licenses/LICENSE.md`。

## 命名说明

任务平台将上游包名 `kicad-library-3d` 拆分为 name=`kicad-library`、version=`3d-10.0.5`（分支 `feat/kicad-library-3d-10.0.5` 与此一致）。本归档严格遵循平台字段，Conan 引用为 `kicad-library/3d-10.0.5`。

## OHOS 适配

这是平台无关的资源包，不生成二进制库或命令行程序，没有 `commands.json`，也没有需要修改的上游 C/C++ 源码。配方不声明 `bindirs`（本地 pre-commit L0k 子串匹配会误判 CLI，且 CI 侧 detect_bindirs.py 按 AST 判定本包为非 CLI）。Conan 配方复用上游 CMake 安装规则，并通过 `KICAD10_3DMODEL_DIR` 导出资源路径，供 KiCad 查找 3D 模型。

上游 `list_models`/`uninstall` 自定义目标不在默认 `all` 目标内，`cmake.build()` 为空构建，不触发 `find|realpath --relative-to` 等工具链问题；`cmake.install()` 执行 `FILES_MATCHING` 过滤安装。

资源内容不因架构变化而变化，`package_id()` 清空包二进制设置；仍保留 `os/compiler/build_type/arch` settings，以满足仓库 OHOS profile 规范和测试包配置。

## 测试口径

上游 `.gitlab-ci.yml` 仅 include 外部 `kicad-library-utils` 的 GitLab CI 模板，源码归档没有本地 CTest 测试，因此上游测试状态记录为 unavailable，不能伪造上游测试通过。适配测试使用消费者探针：

1. 确认安装后根目录恰有 105 个 `.3dshapes` 目录；
2. 每个 `.3dshapes` 目录至少包含 1 个 `.step` 模型；
3. 遍历安装树确认 7245 个 `.step` 文件未被安装过滤丢失；
4. 读取电阻、电容、电池、LED 四个代表性模型，验证 ISO-10303-21 STEP 结构标记（`ISO-10303-21;` / `HEADER;` / `FILE_SCHEMA` / `ENDSEC;` / `END-ISO-10303-21;`）；
5. 对截断的 STEP 输入做负向断言；
6. HarmonyOS 构建使用 `__OHOS__` 编译断言，OHOS 运行时强制 `--require-ohos`。

真机和 Conan/CI 的实际命令、版本、断言数量及结果写入 `reports/test-report.md`。
