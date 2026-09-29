## 基本信息

- **三方库名称**：mobile-broadband-provider-info
- **任务版本 / Conan 包版本**：20240724
- **上游仓库**：https://gitlab.gnome.org/GNOME/mobile-broadband-provider-info
- **适配路径**：路径 A（基础适配）
- **使用知识库**：归档适配经验见 `archives/m/mobile-broadband-provider-info/20240724/notes.md` 和版本 manifest 的 `knowledge_gained`

## 上游版本说明

已先检查 GNOME 官方源码发布目录与 GitLab 标签：没有 `20240724` 目录、源码包或标签；官方发布目录最新可用版本为 `20240407`。因此本 PR 保留任务要求的 Conan 包版本 `20240724`，使用最近的上游源码包 `20240407`，并在配方、清单及笔记中明确标识版本差异。源文件来自官方发布包：
https://download.gnome.org/sources/mobile-broadband-provider-info/20240407/mobile-broadband-provider-info-20240407.tar.xz

SHA-256：`89bfeff215f4bff8e9c3ff2ec25250fdb080d11e9bfa59c6fc71982ac01c814a`（与 GNOME 官方包一致）。

## 测试统计

### 上游测试

| 类型 | 用例数 | 结果 |
|---|---:|---|
| 单元测试 | 0 | 上游无独立单元测试 |
| 集成测试 | 2 | 2/2 通过（Meson `xmllint` 为 OK；`check-blanks` 为上游声明的 EXPECTEDFAIL）|
| **合计** | **2** | **2/2 通过，0 failures，Meson 退出码 0** |

真实 OHOS 设备执行命令：`meson test -C <build-release> --print-errorlogs --no-rebuild`，由本地 `conan create` 的 `build()` 阶段运行。`check-blanks` 在 `meson.build` 中声明 `should_fail: true`；其预期非零 grep 结果被 Meson 计为 EXPECTEDFAIL，而非测试失败。

### 适配后消费者验证

| 验证 | 检查数 | 结果 |
|---|---:|---|
| 安装数据断言 | 19 | 19/19 通过：文件共置、DTD 结构、694 providers、154 countries、APN XML schema、pkg-config 路径解析 |
| Conan 包版本 | 1 | 1/1 通过：依赖引用版本为 20240724 |
| 安装树 DTD 重放 | 1 | 1/1 通过：`xmllint --noout --valid` |
| **合计** | **21** | **21/21 通过** |

`test_package/conanfile.py::test()` 使用 `self.run()` 执行消费者校验脚本，并针对 Conan 已安装包中的 `serviceproviders.xml` 重放 DTD 校验。

## 源码改动与验证

- 未修改上游测试或源文件；适配集中于 Conan 配方和测试配方。
- OHOS PC aarch64 `conan create .../20240724 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：**通过，退出码 0**。
- 构建环境：Meson 1.12.1、Ninja 1.13.2、xsltproc/libxslt 1.1.45_1、OHOS clang 15.0.4。
- 数据包无运行时 Conan 依赖；安装文件仅包含 XML/DTD、生成的 APN XML 和 pkg-config 元数据。
