# yajl 2.1.0 发布说明

**发布日期**: 2026-04-24
**平台**: OpenHarmony aarch64

## 变更摘要

首次为 OpenHarmony 平台编译 yajl 2.1.0。

## 补丁说明

### CMake 4.x 兼容性修复

CMake 4.x 版本废弃了 `GET_TARGET_PROPERTY(target LOCATION)` 语法，导致编译失败。
修改了以下文件使用生成器表达式替代：

1. `reformatter/CMakeLists.txt` - json_reformat 工具
2. `verify/CMakeLists.txt` - json_verify 工具

**修改内容**:
```cmake
# 旧代码 (不兼容 CMake 4.x)
GET_TARGET_PROPERTY(binPath json_verify LOCATION)
ADD_CUSTOM_COMMAND(TARGET json_verify POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${binPath} ${binDir})

# 新代码 (兼容所有 CMake 版本)
ADD_CUSTOM_COMMAND(TARGET json_verify POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_FILE:json_verify> ${binDir})
```

## 包含内容

- `libyajl.so` - 动态链接库
- `libyajl_s.a` - 静态库
- `json_verify` - JSON 格式验证命令行工具
- `json_reformat` - JSON 格式化命令行工具
- 开发头文件 (`yajl/*.h`)

## 安装方式

```bash
tar xzf yajl-2.1.0-ohos-aarch64.tar.gz
cd yajl-2.1.0-ohos-aarch64
./install.sh
```

## 验证安装

```bash
json_verify --help
echo '{"test": true}' | json_verify
```

## 已知问题

无已知问题。

## 测试状态

- 编译测试: ✅ 通过
- 功能测试: ✅ 通过
- 质量门禁: ✅ G1-G4 全部通过

---
*此发布包由 OpenHarmony Compile Agent 自动生成*