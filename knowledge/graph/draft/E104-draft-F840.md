# E104: euidaccess 函数未定义

## 错误特征

编译时出现未定义标识符错误：
```
ict-main.cpp:507:16: error: use of undeclared identifier 'euidaccess'; did you mean 'eaccess'?
      else if (euidaccess(cfg.c_str(), R_OK) != 0) {
               ^~~~~~~~~~
               eaccess
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/unistd.h:205:5: note: 'eaccess' declared here
int eaccess(const char *, int) __attribute__((__availability__(ohos, introduced=12.0.0)));
```

## 触发条件
- 构建系统: Makefile / autotools / cmake
- 阶段: compilation（编译阶段）
- 项目类型: 使用 GNU euidaccess 函数检查文件访问权限的项目

## 根因分析

OpenHarmony 使用 `eaccess` 函数替代 GNU 的 `euidaccess` 函数。这是平台 API 差异：

- **GNU/Linux**: 提供 `euidaccess` 函数（GNU 扩展），检查有效用户 ID 的文件访问权限
- **OpenHarmony**: 提供 `eaccess` 函数（OHOS API 12+），功能类似但名称不同

编译器建议使用 `eaccess` 替代，说明 OpenHarmony 的 unistd.h 中定义了 `eaccess` 但没有 `euidaccess`。

## 解决方案

### 方案 A：源码替换（推荐）

直接修改源码，将 `euidaccess` 替换为 `eaccess`：

```bash
# 方案 1: 使用 sed 批量替换
sed -i 's/euidaccess(/eaccess(/g' source.cpp

# 方案 2: 手动编辑
vim source.cpp
# 找到 euidaccess 调用，替换为 eaccess
```

示例修改（incron 0.5.12）：
```cpp
// 修改前
else if (euidaccess(cfg.c_str(), R_OK) != 0) {

// 修改后
else if (eaccess(cfg.c_str(), R_OK) != 0) {
```

### 方案 B：宏定义映射

如果不想修改源码，可以在编译配置中添加宏定义：

```bash
# 在 config.h 或编译选项中添加
echo '#define euidaccess(path, mode) eaccess(path, mode)' >> config.h

# 或在编译选项中
CXXFLAGS += -Deuidaccess=eaccess
```

### 补丁生成

生成补丁文件以便复用：
```bash
# 创建补丁
cd incron-0.5.12
git diff > 0001-euidaccess-to-eaccess.patch

# 应用补丁
patch -p1 < 0001-euidaccess-to-eaccess.patch
```

### 禁止做法
- ❌ 不要尝试链接 GNU libc 库（OpenHarmony 使用 musl libc）
- ❌ 不要尝试从其他系统复制 unistd.h（可能导致更多兼容性问题）

## 验证

修改后验证：
```bash
# 检查源码中是否还有 euidaccess
grep -r "euidaccess" *.cpp *.c 2>/dev/null && echo "Still has euidaccess" || echo "All euidaccess replaced"

# 编译测试
make clean && make
```

## 受影响位置

以 incron 0.5.12 为例：
- `ict-main.cpp:507` - 配置文件权限检查

其他可能受影响的项目：
- 使用 GNU euidaccess 进行权限检查的软件
- 从 Linux 移植到 OpenHarmony 的系统工具

## 关联条目
- 相关: E025 (API 差异), E042 (函数重命名)
- 应用: incron, 其他使用 euidaccess 的项目

## API 对比

| 函数 | GNU/Linux | OpenHarmony | 说明 |
|------|-----------|-------------|------|
| `euidaccess` | ✅ | ❌ | GNU 扩展 |
| `eaccess` | ✅ | ✅ | POSIX 标准化（部分系统） |

**注意**: OpenHarmony 的 `eaccess` 需要 OHOS API 12.0.0 或更高版本。

## 历史

- 2026-05-26: 首次发现（incron 0.5.12 编译）
- 2026-05-27: 知识条目创建