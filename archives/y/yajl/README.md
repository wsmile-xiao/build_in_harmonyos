# yajl 2.1.0 — OpenHarmony 编译记录

## 基本信息
- 软件: yajl (Yet Another JSON Library)
- 版本: 2.1.0
- 构建系统: CMake
- 目标: ohos-aarch64
- 编译日期: 2026-04-24

## 编译指导
使用 CMake 构建系统，需要以下补丁修复 CMake 4.x 兼容性问题。

```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 补丁清单
| 补丁文件 | 说明 |
|---------|------|
| 0001-reformatter-CMakeLists.txt.patch | 修复 json_reformat 的 CMake LOCATION 属性废弃问题 |
| 0002-verify-CMakeLists.txt.patch | 修复 json_verify 的 CMake LOCATION 属性废弃问题 |

**问题**: CMake 4.x 废弃了 `GET_TARGET_PROPERTY(... LOCATION)` 语法
**解决**: 使用生成器表达式 `$<TARGET_FILE:target>` 替代

## 已知限制
- 无标准测试套件，需手动验证二进制功能

## 功能验证
```bash
# 验证 JSON 格式
echo '{"name":"test"}' | json_verify
# 输出: JSON is valid

# JSON 格式化
echo '{"name":"test"}' | json_reformat
```

## 产物
- libyajl.so (动态库)
- libyajl_s.a (静态库)
- json_verify (JSON 验证工具)
- json_reformat (JSON 格式化工具)
