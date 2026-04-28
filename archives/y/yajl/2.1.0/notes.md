# yajl 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake GET_TARGET_PROPERTY LOCATION 废弃 | CMake 4.x 不支持旧语法 | 使用生成器表达式 $<TARGET_FILE:target> 替代 |

## 源码修改
- 0001-reformatter-CMakeLists.txt.patch: 替换 LOCATION 属性
- 0002-verify-CMakeLists.txt.patch: 替换 LOCATION 属性

## 验证结果
- echo '{"name":"test"}' | json_verify → JSON is valid ✅
- echo '{"name":"test"}' | json_reformat → 格式化输出 ✅

## 交付物
- libyajl.so / libyajl_s.a
- json_verify, json_reformat

## 注意事项
- 无标准测试套件
