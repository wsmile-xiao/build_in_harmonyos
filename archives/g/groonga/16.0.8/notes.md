# groonga 16.0.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-31
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cmake -DGRN_WITH_ZLIB=yes -DGRN_WITH_LZ4=yes -DGRN_WITH_XXHASH=no \
      -DGRN_WITH_RAPIDJSON=yes -DGRN_WITH_APACHE_ARROW=no \
      -DGRN_WITH_ZSTD=no -DGRN_WITH_LLAMA=no
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI worker 缺 aclocal/autoreconf | autotools 构建需 automake 工具链 | 改用上游官方 CMake 构建（CMakeLists.txt 完整支持） |
| 2 | xxhash/rapidjson bundled vs 外部 | 项目 xxhash 包无 CMake config，rapidjson 未发布 | xxhash/rapidjson 用 groonga bundled（vendor/），zlib/lz4 用项目外部包 |
| 3 | zstd/llama 下载失败或平台不兼容 | CI 网络受限 / OHOS 不支持 AI 嵌入 | 全部禁用（GRN_WITH_ZSTD=no、GRN_WITH_LLAMA=no） |

## 依赖版本

- zlib/1.3.1（项目已适配包）
- lz4/1.10.0（项目已适配包）
- xxhash/rapidjson 用 groonga bundled 版本

## 验证结果

```bash
groonga --version
```

## 交付物

| 文件 | 说明 |
|------|------|
| libgroonga | 全文搜索引擎核心库 |
