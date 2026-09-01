# json-schema-validator 2.1.0 适配笔记

## 官方来源核验（R01 bootstrap）
- 官方仓库：https://github.com/pboettch/json-schema-validator
- 标签：`2.1.0`（git ls-remote refs/tags/2.1.0 -> 27fc1d094503623dfe39365ba82581507524545c）
- 默认分支：main（HEAD 0a5c207a8a02dae8c781a205b7746395fbee1f56）
- tarball：https://github.com/pboettch/json-schema-validator/archive/refs/tags/2.1.0.tar.gz
- SHA-256：83f61d8112f485e0d3f1e72d51610ba3924b179926a8376aef3c038770faf202（实测下载校验）
- 许可证：MIT
- GitHub release API 对该标签未返回对象（仓库该版本可能仅打 tag 未建 release 页），
  但 git tag 权威存在，tarball 下载成功且校验一致。

## 项目结构
- CMake 库项目（cmake_minimum_required 3.2，LANGUAGES CXX）
- 库目标：nlohmann_json_schema_validator（src/*.cpp）
- 公共头：src/nlohmann/json-schema.hpp（安装到 include/nlohmann/）
- 示例可执行：json-schema-validate、readme-json-schema（app/）
- 测试：test/（ctest 驱动，含 JSON-Schema-Test-Suite 子模块依赖）

## 依赖
- 唯一第三方依赖：nlohmann_json（header-only）
- 上游 Conan 1.x 配方锁定 nlohmann_json/3.7.3
- ohpcd 制品仓已发布：nlohmann_json/3.1.1、nlohmann_json/3.12.0（未见 3.7.3）
- 适配阶段需实证 3.12.0（或 3.1.1）与上游 CMake 逻辑的兼容性，必要时调整版本引用

## 上游配方（Conan 1.x）要点
- name = 'JsonSchemaValidator'（大写，需转 Conan 2.x 小写包名）
- generators = "cmake"；依赖 nlohmann_json/3.7.3
- build(): -Dnlohmann_json_DIR 指向 deps include；BUILD_EXAMPLES=True BUILD_TESTS=False
- package_info(): includedirs=include；libs=tools.collect_libs；PATH 追加 bin（示例可执行）

## 首轮本地验证结论
（待补充：smoke test + 上游测试结果）
---

**编译结束**: 2026-08-31 15:39
**最终状态**: built
