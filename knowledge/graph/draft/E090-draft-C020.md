# E090: cmake模块丢失导致configure失败

## 问题

在使用 `ohc-run.py build` 自动管线编译mongo-c-driver/libbson时，build管线重新初始化 `.work` 目录，清空了 `build/cmake/` 子目录中的所有cmake模块文件（BuildVersion.cmake, ParseVersion.cmake, LoadVersion.cmake, MongoSettings.cmake, MongoPlatform.cmake等），导致后续cmake配置步骤无法找到这些必需模块，configure失败。

## 根因

`ohc-run.py build` 的初始化步骤会重新解压tarball到 `.work` 目录。对于使用嵌套 `build/cmake/` 目录结构的项目（如mongo-c-driver），如果 `.work` 目录已存在但被部分修改（如cmake cache等），重初始化会清空或覆盖这些内容。

## 解决方案

1. **推荐方案（模式B）**：使用手动cmake/make编译模式，避免build管线重初始化 `.work` 目录。如果 `.work` 目录已被重初始化，从 `.orig` 目录复制 `build/cmake/` 恢复cmake模块：
   ```bash
   cp -r $BUILD_SRC_ORIG_DIR/build/cmake $BUILD_SRC_DIR/build/cmake
   cd $BUILD_SRC_DIR
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_SYSTEM_NAME=Linux <其他选项> .
   make -j2
   make install DESTDIR=$TEST_PREFIX
   ```

2. **回退方案**：使用Savannah官方发布tarball而非GitHub archive，因为Savannah tarball包含所有生成的cmake模块，而GitHub archive不包含。

## 影响范围

所有使用嵌套 `build/cmake/` 目录结构的项目，特别是mongo-c-driver及其子项目（libbson、libmongoc）。

## 验证命令

```bash
ls $BUILD_SRC_DIR/build/cmake/BuildVersion.cmake
```

## 禁止策略

❌ 不要对libbson/mongo-c-driver使用 `ohc-run.py build` 自动管线，因为它会重初始化 `.work` 目录导致cmake模块丢失。