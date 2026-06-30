# libsmi 0.5.0 Release Notes

## 版本信息
- **软件**: libsmi
- **版本**: 0.5.0
- **发布日期**: 2014-10-13
- **编译日期**: 2026-05-15
- **目标平台**: ohos-aarch64 (HarmonyOS)

## 编译状态
- **总体状态**: success (功能完整，预编译包已生成)
- **构建系统**: autotools
- **编译器**: clang 15.0.4

## 主要变更

### 平台适配
1. **E007 修复**: config.guess 添加 HarmonyOS 平台识别
2. **HMDFS workaround**: 修改 config.status 使用 $TMPDIR 临时目录

### 测试结果
- 单元测试: 18/20 PASS
- 功能验证: ✅ PASS
- MIB 解析: ✅ PASS

## 已知限制

| 编号 | 限制 | 影响 | 解决方案 |
|------|------|------|---------|
| F001 | HMDFS config.status 临时目录 | 配置阶段 | 预创建临时目录 |
| F002 | RPATH 配置 | 运行时 | 设置 LD_LIBRARY_PATH |
| F003 | G0 干净构建验证 | 验证阶段 | 手动验证通过 |
| F004 | 测试数据缺失 | 非关键 | 不影响功能 |

## 补丁文件
- `0001-config.guess.patch` - HarmonyOS 平台识别 (核心补丁)
- 其他补丁为生成文件变更

## 编译产物
- libsmi.so.2.0.27 (1.1MB) - 共享库
- libsmi.a (1.7MB) - 静态库
- smidump, smilint, smiquery 等工具 (~1.5MB)
- MIB/YANG 数据文件 (~2MB)

## 使用说明
```bash
# 设置环境
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 验证安装
smidump --version
smilint --version
pkg-config --modversion libsmi

# 解析 MIB 文件
smidump -f tree /path/to/MIB
smilint /path/to/MIB
```

---
**编译者**: OpenHarmony Compile Agent
**归档路径**: archives/l/libsmi/0.5.0/