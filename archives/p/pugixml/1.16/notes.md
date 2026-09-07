# pugixml 1.16 适配记录

## 来源与依赖

- 官方仓库：https://github.com/zeux/pugixml
- 标签：v1.16
- 归档 SHA-256：357BCAB8877DC9943F355D3A72DABA1B053238BA955F50FA81586AFB65090219
- Conan 依赖：无；官方 CMake 只编译 pugixml 源文件。

## 适配边界

Conan `shared` 选项映射到上游 `BUILD_SHARED_LIBS`，默认静态构建；CMake
导出的 `pugixml::pugixml` 目标和 `pugixml` 库名在 package_info 中保持一致。
上游 CMake 提供一个 `pugixml-check` CTest 目标，完整主机测试作为上游 1/1
证据；目标侧另用 consumer 验证安装头文件、解析和 XPath 公共 API。

## 验证

Conan create、上游 CTest 和 test_package 构建通过。交叉构建的 consumer 在
授权 OpenHarmony PC 端点上运行，验证 XML 解析与 XPath 查询，进程正常退出。

## 新增知识

- E552：独立 CMake 库通过 BUILD_SHARED_LIBS 和导出目标名映射 Conan shared
  选项时，需同时回读生成的 CMake config 和实际库文件名。
- E553：上游 CTest 可在主机独立执行并绑定 1/1；交叉构建测试只能把运行边界
  延后到真机 consumer，不能把主机运行结果冒充目标运行结果。

---

**编译结束**: 2026-09-04
**最终状态**: built
