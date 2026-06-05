# E093 — Git Submodule Missing from Release Tarball

## 错误特征
编译配置阶段出现以下错误：
- `framework/exported.make: No such file or directory`
- `fatal: not a git repository (or any of the parent directories): .git`
- 缺少预期的子目录（如 `framework/`）

## 触发条件
- 构建系统: cmake/autotools
- 阶段: configuration
- 软件使用 git submodules（如 mbedtls）
- 源码来自 GitHub/Gitee release tarball（非 git clone）

## 根因分析
GitHub/Gitee 的 release tarball 不包含 submodule 内容，只包含 `.gitmodules` 文件。
导致依赖 submodule 的构建系统无法找到必需的文件（如 mbedtls 的 framework/ 目录）。

这是 release tarball 与 git clone 的根本差异，不是用户操作错误。

## 解决方案

### 推荐方案（手动下载 submodule）
1. 检查 `.gitmodules` 文件确认 submodule 名称和 URL
2. 从对应 GitHub 仓库下载 submodule（使用 `git clone --depth=1`）
3. 复制到源码目录的正确位置
4. 验证必需文件存在

```bash
# 示例：mbedtls framework submodule
git clone --depth=1 https://github.com/Mbed-TLS/mbed-framework.git framework
cd framework
git checkout $(grep -A1 'framework' ../../.gitmodules | grep 'commit' | awk '{print $2}')
```

### 回退方案（使用完整 git clone）
如果下载 submodule 困难，可以：
1. 删除 tarball 解压的源码
2. 使用 `git clone --recursive` 重新克隆完整仓库

```bash
git clone --recursive --depth=1 https://github.com/Mbed-TLS/mbedtls.git mbedtls-v3.6.0
```

### 禁止做法
- ❌ 在 tarball 解压目录执行 `git submodule update --init`（会失败，因为不是 git 仓库）
- ❌ 手动创建空目录（无法解决文件缺失问题）

## 验证
```bash
# 检查 submodule 目录是否完整
ls -la framework/
test -f framework/exported.make

# 重新运行 configure
cmake -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 .
```

## 关联条目
- 相关: E007 (config.guess 平台识别)
- 相关: E046 (SELinux 权限限制)
