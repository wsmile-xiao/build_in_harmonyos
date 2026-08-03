# rbenv-bundle-exec 1.0.0 适配笔记

## 编译环境

- 构建系统: custom（纯 Bash 脚本插件，无需 native 编译）
- 编译日期: 2026-07-27
- 编译器: clang/clang++（本项目未调用编译器）
- 状态: built

## 编译步骤

1. 按 SKILL.md 加载 openharmony-compile-agent 流程要求。
2. 通过上游标签 `v1.0.0` 获取源码：
   ```bash
   python3 scripts/ohc-run.py init-build rbenv-bundle-exec 1.0.0 \
     --url=https://github.com/maljub01/rbenv-bundle-exec/archive/refs/tags/v1.0.0.tar.gz \
     --tar=tar.gz
   ```
3. 确认项目为纯 Bash 插件，无 `configure`、`Makefile`、`CMakeLists.txt` 等 native 构建入口。
4. 上游文件结构（仅有 3 个文件）：
   ```
   etc/rbenv.d/exec/bundle-exec.bash   # rbenv exec 钩子脚本 (~40行)
   LICENSE                              # MIT 许可证
   README.md                            # 项目文档
   ```
5. 手动安装到 staging：
   ```bash
   mkdir -p "$TEST_PREFIX/$DEFAULT_PREFIX/share/rbenv-bundle-exec/etc/rbenv.d/exec"
   cp etc/rbenv.d/exec/bundle-exec.bash \
     "$TEST_PREFIX/$DEFAULT_PREFIX/share/rbenv-bundle-exec/etc/rbenv.d/exec/"
   cp README.md LICENSE "$TEST_PREFIX/$DEFAULT_PREFIX/share/rbenv-bundle-exec/"
   ```
6. 编写 Conan 配方，`build()` 为空操作，`package()` 复制 Bash 钩子脚本、README 和 LICENSE。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次使用 GitHub archive URL 下载失败 | 远端关闭连接 | 改用 GitHub API tarball URL |
| 2 | init-build 未识别构建文件 | 该项目是纯 Bash 脚本插件 | 采用 custom/no-op build，直接复制脚本打包 |
| 3 | 初始 conanfile.py 误包含 bin/* 复制 | 未核实上游文件结构 | 核实后移除 bin/* 引用，上游无 bin/ 目录 |
| 4 | conan create 测试失败：bundle-exec.bash 路径嵌套 | copy() pattern 保留相对路径，dst 已包含 etc/rbenv.d/exec | 将 dst 从 plugin_dir/etc/rbenv.d/exec 改为 plugin_dir |
| 5 | apply_conandata_patches 位置不符规范 | 原在 build() 中调用 | 移至 source() 方法中 get() 之后 |

## 源码修改

无源码补丁，`patches_applied: []`。

## 依赖版本

- 运行依赖: rbenv, Ruby >= 1.8.7, Bundler gem
- 编译依赖: 无

## 验证结果

```bash
# conan create + test_package 验证（Windows x86_64, conan 2.29.1）
conan create . --name=rbenv-bundle-exec --version=1.0.0 --build=missing
# → 构建成功，3 个文件打包（LICENSE, README.md, bundle-exec.bash）
# → test_package 通过：文件存在性检查通过
# → bash 语法检查在 Windows 上跳过（bash 不在 PATH），CI 在 OHOS 上会执行

# 打包产物结构
# share/rbenv-bundle-exec/LICENSE
# share/rbenv-bundle-exec/README.md
# share/rbenv-bundle-exec/etc/rbenv.d/exec/bundle-exec.bash
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方，纯脚本打包 |
| conandata.yml | 上游源码 URL 与 sha256 |
| test_package/conanfile.py | Conan smoke test（文件检查 + bash 语法检查） |
| test_package/MANIFEST.yml | 测试声明文件 |
| test_package/test.sh | test_package 源文件占位与文件存在检查 |
| manifest.yaml | 版本级元数据 |
| notes.md | 适配笔记 |

## 注意事项

用户需将插件目录链接到 rbenv 插件路径：

```bash
export RBENV_ROOT="${RBENV_ROOT:-$HOME/.rbenv}"
ln -sf "$HOME/usr/local/share/rbenv-bundle-exec" "$RBENV_ROOT/plugins/rbenv-bundle-exec"
```

插件会自动通过 `etc/rbenv.d/exec/bundle-exec.bash` 钩子被 rbenv 加载，无需额外配置。