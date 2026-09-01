# csv-parser 1.1 适配笔记

## 软件信息
- 名称: csv-parser (p-ranav/csv)
- 版本: 1.1
- 类型: Header-only C++17 库
- 许可证: MIT
- 上游: https://github.com/p-ranav/csv

## 构建系统
- CMake (仅用于测试)
- 无需编译，header-only

## 适配要点
1. header-only 库，package_type = "header-library"
2. 需要 C++17 (compiler.cppstd=17)
3. 源码结构: include/csv/*.hpp (reader, writer, dialect, concurrent_queue, robin_hood)
4. 无外部依赖
5. 无需补丁

## 验证结果
- G1 配方完整性: PASS
- G2 conan create: PASS
- G3 系统同名库隔离: PASS
- W3 本地 CI 模拟: PASS (setup.sh + build_and_test.sh)
