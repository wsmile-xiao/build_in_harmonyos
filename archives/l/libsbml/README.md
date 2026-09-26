# libsbml

Systems Biology Markup Language (SBML) 的读写与操作库, C/C++ 实现。

## OHOS 适配

- 使用 libxml2 作为 XML 解析后端, zlib/bzip2 提供压缩支持。
- 上游 ctest + libcheck 测试套件在构建期运行。
- 消费者测试覆盖核心建模与写读回环。

## 依赖

- libxml2/2.15.3
- zlib/1.3.1
- bzip2/1.0.8
- check/0.15.2 (仅测试)

## 参考

- 上游: https://github.com/sbmlteam/libsbml
- 文档: https://sbml.org/software/libsbml/
