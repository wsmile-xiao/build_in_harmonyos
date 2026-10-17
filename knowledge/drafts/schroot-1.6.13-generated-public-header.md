# configure 期生成的公共头未安装：消费者编译必然失败

- **草稿 ID**: DRAFT-SCHROOT-1613-GENERATED-PUBLIC-HEADER
- **条目文件**: `knowledge/drafts/schroot-1.6.13-generated-public-header.kv`
- **来源事件**: schroot 1.6.13 消费者用例构建（2026-10-01）
- **严重程度**: 🔴 blocking

## 1. 现象

本包自身 `conan create` 编译一路通过，但**独立消费者**（test_package 的 C++ 程序）
只要 include 包内公共头就编译失败：

```
.../include/sbuild/sbuild-i18n.h:27:10: fatal error: 'sbuild/sbuild-config.h' file not found
```

而该头在**构建树**里明明存在（生成目录内）。

## 2. 根因

上游用 `configure_file()` / `AC_CONFIG_HEADERS` 生成平台配置宏头（schroot 为
`sbuild-config.h`），该文件落在**构建目录**，不在源码树 `include/` 下。
上游 install 规则按源码树的 include 清单安装——于是包内有 `sbuild-i18n.h`、`sbuild-util.h`，
**唯独缺 `sbuild-config.h`**，而它们 `#include` 了它。

症状具有欺骗性：

- 构建期自身编译能过（构建目录里该头可见）；
- 只有**独立消费者**（不共享构建目录）才会暴露 ⇒ 必须用真实消费者验证。

## 3. 解决方案

在 `package()` 中把构建树里生成的公共头复制进包内、保持与上游 `#include` 路径一致：

```python
shutil.copyfile(
    os.path.join(self.build_folder, "build", "Release", "sbuild", "sbuild-config.h"),
    os.path.join(self.package_folder, "include", "sbuild", "sbuild-config.h"),
)
```

同时确保 `package_info()` 暴露 `includedirs=["include"]`，让 CMakeDeps / PkgConfigDeps
给出正确的 `-I`。若上游提供了安装开关（如 `CONFIGURE_HEADER_INSTALL_DIR` 之类 CACHE 变量），
优先传变量而非拷贝。

## 4. 禁止做法

- ❌ 改上游公共头的 `#include` 为相对路径（如 `"../sbuild-config.h"`）——把构建目录布局写进对外接口，
  换消费者环境必挂，属"假绿"。
- ❌ 只在 test_package 里额外 `include_directories(<build tree>)` 让测试跑过——
  真实下游拿不到该目录，问题只是被推迟到 CI/用户侧。

## 5. 验证

```bash
# 包内是否装了生成头
find <package_folder>/include -name '*config.h'

# 最小消费者：只 include 公共头并编译（不借助构建树任何路径）
echo '#include <sbuild/sbuild-util.h>' > t.cpp && clang++ -I<package_folder>/include -c t.cpp -o /dev/null && echo OK
```

## 6. 适用范围

所有 autotools/CMake 项目中「生成头对外可见、但 install 只装源码树 include/」的包；
`configure_file(... .h)`、`AC_CONFIG_HEADERS`、xgettext 模板头都是同类信号。
