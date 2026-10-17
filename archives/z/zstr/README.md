# zstr

zstr 是一个 C++ header-only 的 zlib 封装库，提供标准 iostream 接口
（`zstr::ifstream/ofstream/istream/ostream`）读写 zlib 压缩流，附带
`strict_fstream.hpp` 严格文件流辅助头。

- 官方仓库：https://github.com/mateidavid/zstr
- 许可证：MIT
- 版本：1.1.0（标签 `v1.1.0`）
- 目录结构：`archives/z/zstr/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
- 依赖：`zlib/1.3.1`（消费时透传）
