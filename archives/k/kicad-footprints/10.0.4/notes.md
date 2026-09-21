# kicad-footprints 10.0.4 适配笔记

## 上游与产物

- 使用 KiCad 官方 GitLab `kicad-footprints` 项目的 10.0.4 归档。
- 归档 SHA-256 为 `bd9ac36dd8bc5ae9089cf7593d2e8137dc5d3ce35d75e870aa3cd497f2070d0e`。
- 上游清单包含 155 个 `*.pretty` footprint 库目录和 15435 个 `*.kicad_mod` 文件。
- 上游 `CMakeLists.txt` 使用 `project(kicad-footprints NONE)`，将 footprint 库安装到 `share/kicad/footprints`，并将 `fp-lib-table` 安装到 `share/kicad/template`。
- `LICENSE.md` 为 CC-BY-SA-4.0，本包原样保留到 `licenses/LICENSE.md`。

## OHOS 适配

这是平台无关的资源包，不生成二进制库或命令行程序，因此没有 `commands.json`，也没有需要修改的上游 C/C++ 源码。Conan 配方复用上游 CMake 安装规则，并通过 `KICAD10_FOOTPRINT_DIR` 导出资源路径，供 KiCad 库表解析。

资源内容不因架构变化而变化，`package_id()` 清空包二进制设置；仍保留 `os/compiler/build_type/arch` settings，以满足仓库 OHOS profile 规范和测试包配置。

## 测试口径

上游 `.gitlab-ci.yml` 仅 include 外部 `kicad-library-utils` 的 footprint CI 模板，源码归档没有本地 CTest 测试，因此上游测试状态记录为 unavailable，不能伪造上游测试通过。适配测试使用消费者探针：

1. 读取安装后的 `fp-lib-table`，确认 155 个库表项与 155 个 `.pretty` 目录一致；
2. 遍历安装树确认 15435 个 `.kicad_mod` 文件未被安装过滤丢失；
3. 读取 DIP、Molex 和 0603 电阻代表性文件，验证 KiCad footprint 的基本 S-expression 字段和括号配平；
4. 对截断的 footprint 输入做负向断言；
5. HarmonyOS 构建使用 `__OHOS__` 编译断言，OHOS 运行时强制 `--require-ohos`。

真机和 Conan/CI 的实际命令、版本、断言数量及结果写入 `reports/test-report.md`。
