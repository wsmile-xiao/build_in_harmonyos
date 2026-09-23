# kicad-library-templates 10.0.5 移植记录

## 上游

- 官方仓库：<https://gitlab.com/kicad/libraries/kicad-templates>
- 标签：`10.0.5`
- 提交：`3ed4538b0f965d821df63a5fffc4441e723cfe7f`
- 源归档 SHA-256：`bb42390db45f8a6b1539c6f83850ad2091506b6a63598049b4bc805900491145`
- 许可证：CC-BY-SA 4.0（包含 KiCad Libraries 设计文件例外）

上游 CMake 工程为 `project(kicad-templates NONE)`，只安装 `Projects/*` 和
`Worksheets/*.kicad_wks`，没有独立测试目录或 CTest 测试目标。

## 资源布局

- 19 个 `Projects` 工程模板根目录；
- 36 个 `.kicad_wks` worksheet，安装到 template 根目录；
- 上游非 Git 文件总数：184；
- Conan 资源区（`Projects` + `Worksheets`）文件总数：177。

Conan 产物资源根目录为 `share/kicad/template`，通过 `cpp_info.resdirs` 和
`KICAD_TEMPLATE_DIR` 暴露给下游。

## 测试

- 上游测试：0（上游仓库没有测试目标）。
- 适配测试：2 个测试程序：通用资源消费者、HarmonyOS 专项消费者。
- 通用消费者检查工程目录、177 个资源文件、关键扩展名数量及 KiCad 文件头部。
- HarmonyOS 消费者检查 `__OHOS__`、`__aarch64__`/`__x86_64__`，并用 POSIX
  `open/read` 读取一个工程模板和一个 worksheet。

## 验证记录

- Windows host Conan create：通过；资源清单和通用 consumer test 通过。
- DevEco HarmonyOS 6.0 SDK armv8 交叉 Conan create：专项测试目标编译通过，运行按
  `can_run()` 延后。
- DevEco HarmonyOS 6.0 SDK x86_64 交叉 Conan create：通用和 HarmonyOS 专项目标编译通过，
  并在 `Huawei_2in1` HarmonyOS 6.0 PC VM（HDC `127.0.0.1:16555`）中实际运行通过。
- VM 通用消费者输出：`19 projects, 36 worksheets, 177 resource files`；HarmonyOS 专项消费者
  输出：`__OHOS__`、x86_64 架构宏和 POSIX `open/read` 读取均通过。
- `graph validate`：通过（仓库知识图谱已有警告，不属于本归档）。
- `tests/run_all.py`：12 套中 11 套通过；`test_v1220.py` 在 Windows 环境因缺少被测
  外部可执行文件而失败，已保留原始错误证据。
- HarmonyOS 6.0 `Huawei_2in1` VM 已完成实际验证：x86_64 测试程序部署到专用临时目录，
  资源目录和两个消费者测试均运行通过。
---

**编译结束**: 2026-09-20 00:46
**最终状态**: built
