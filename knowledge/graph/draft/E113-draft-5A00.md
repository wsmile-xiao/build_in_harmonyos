# E113 — 嵌套源码提升丢失同级目录导致 CMake 构建失败

## 错误特征
- CMake 配置时报 `include_directories(../include)` 找不到目录
- `make` 时找不到头文件（如 `toml.h: No such file or directory`）
- G0 干净构建验证补丁应用失败：`CMakeLists.txt: No such file or directory`

## 触发条件
- 构建系统: cmake（也影响 autotools 等其他系统）
- 阶段: configuration（init-build 的 _promote_nested_source 步骤）

## 根因分析
`init-build` 的 `_promote_nested_source` 函数在检测到子目录（如 `src/`）中存在构建文件（CMakeLists.txt）后，会将该子目录的内容提升到顶层。提升过程中，步骤 2 会删除顶层目录中所有非点号开头的文件和目录（包括 `include/`、`testcase/`、`LICENSE`、`README.md` 等），导致这些同级目录丢失。

对于 `src/` + `include/` 分离结构的项目（如 header-only 库 tinytoml），这会导致 CMakeLists.txt 中引用的 `../include` 和 `../testcase` 路径失效。

## 解决方案

### 推荐方案
1. 从原始 tarball 重新解压到临时目录
2. 将丢失的目录（`include/`、`testcase/`）复制到工作目录
3. 修改 CMakeLists.txt 中的路径：`../include` → `include`，`../testcase` → `testcase`
4. 用 `track-edit` 追踪 CMakeLists.txt 的修改

```bash
tar xzf $BUILD_TARBALL -C $HOME/tmp/tinytoml-extract
cp -r $HOME/tmp/tinytoml-extract/<name>-<ver>/include $BUILD_SRC_DIR/
cp -r $HOME/tmp/tinytoml-extract/<name>-<ver>/testcase $BUILD_SRC_DIR/
sed -i 's|../include|include|g; s|../testcase|testcase|g' $BUILD_SRC_DIR/CMakeLists.txt
```

### 注意事项
- 修改后的 CMakeLists.txt 仅适用于提升后的目录结构
- 不要生成补丁文件（因为补丁针对提升后结构，无法应用于原始 tarball）
- G0 干净构建验证会因路径差异失败，这是已知限制

### 禁止做法
- ❌ 不要为提升后的 CMakeLists.txt 修改生成补丁（补丁无法应用于原始 tarball 结构）
- ❌ 不要删除已恢复的同级目录

## 验证
```bash
ls $BUILD_SRC_DIR/include/toml/toml.h && echo "OK"
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j2 && make test
```

## 关联条目
- 相关: E007（config.guess 平台不识别）
