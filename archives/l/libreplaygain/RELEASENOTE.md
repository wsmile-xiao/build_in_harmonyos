# libreplaygain — HarmonyOS aarch64 预编译包

## 快速安装

### 方法 1: 使用安装脚本
```bash
tar xzf libreplaygain-r475-ohos-aarch64.tar.gz
cd libreplaygain-r475-ohos-aarch64
sh install-libreplaygain-r475.sh
```

### 方法 2: 手动安装
```bash
tar xzf libreplaygain-r475-ohos-aarch64.tar.gz -C ~/usr/local --strip-components=1
```

---

## 可用版本

| 版本 | 状态 | 补丁数 | 编译日期 | 包大小 |
|------|------|--------|----------|--------|
| r475 | ✅ 成功 | 1 | 2026-05-11 | 93K |

---

## 当前版本 (r475) 详情

### 包内容
- **二进制文件**: 无（库项目）
- **静态库**: `lib/libreplaygain.a` (12K)
- **共享库**: `lib/libreplaygain.so` (27K)
- **包大小**: 93K (主包) + 26K (调试符号包)

### 编译信息
- **构建系统**: CMake
- **编译器**: clang 15.0.4
- **目标平台**: HarmonyOS aarch64
- **质量门禁**: ✅ G1-G4 全部通过
- **补丁数**: 1

### 补丁列表
- `0001-cmake-version.patch`: 更新 CMake 最小版本要求从 2.4 到 3.5

### 库功能
libreplaygain 提供以下核心功能：
- `InitGainAnalysis()` - 初始化增益分析
- `AnalyzeSamples()` - 分析音频样本
- `GetTitleGain()` - 获取单曲增益值
- `GetAlbumGain()` - 获取专辑增益值
- `ResetSampleFrequency()` - 重置采样频率

---

## 环境要求

### 系统要求
- **操作系统**: HarmonyOS/OpenHarmony aarch64
- **架构**: ARM64 (aarch64)

### 使用说明
libreplaygain 是音频 ReplayGain 标准的实现库，需要在其他音频处理软件中集成使用。

#### 编译依赖此库的项目
如果您的项目需要使用 libreplaygain，在编译时链接该库：

```bash
# 使用静态库
clang your-program.c -lreplaygain -L~/usr/local/lib -I~/usr/local/include

# 使用共享库
clang your-program.c -lreplaygain -L~/usr/local/lib -I~/usr/local/include -Wl,-rpath,~/usr/local/lib
```

---

## 安装验证

安装完成后，可通过以下命令验证：

```bash
# 检查库文件
ls -lh ~/usr/local/lib/libreplaygain.*

# 查看符号
nm ~/usr/local/lib/libreplaygain.a | grep GainAnalysis
```

预期输出应包含：
- `libreplaygain.a` - 静态库文件
- `libreplaygain.so` - 共享库文件
- 符号表中包含 `InitGainAnalysis`、`AnalyzeSamples` 等函数

---

## 已知问题

1. **编译警告**: GNU folding constant 警告（非关键，不影响功能）
2. **无测试套件**: 项目不包含自动化测试，需在实际使用中验证

---

## 下载链接

### 主包
`libreplaygain-r475-ohos-aarch64.tar.gz` (93K)

### 调试符号包
`libreplaygain-r475-ohos-aarch64-debug.tar.gz` (26K)

---

## 更新历史

### r475 (2026-05-11)
- ✅ 初次编译成功
- ✅ 通过质量门禁 G1-G4
- ✅ 生成预编译包
- ⚠️ 需要更新 CMake 版本要求（已通过补丁修复）

---

**维护者**: OpenHarmony 编译团队  
**更新日期**: 2026-05-11