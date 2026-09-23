# dawgdic

dawgdic 是以双数组为底层结构的 DAWG（有向无环词图）词典构建与查询 C++ 库：以确定性有限自动机最小化 Trie，内存占用小，查询速度与 Darts 双数组 Trie 相当。

本目录打包上游 0.4.5，提供头文件库（`include/dawgdic/`，23 个头文件）与 `dawgdic-build`、`dawgdic-find` 两个命令行工具。

## 使用示例

```bash
printf 'a\t1\nan\t0\nand\t2\n' > lexicon
dawgdic-build -t lexicon lexicon.dic
echo "an" | dawgdic-find lexicon.dic
```

```cpp
#include <dawgdic/dawg-builder.h>
#include <dawgdic/dictionary-builder.h>
#include <dawgdic/dictionary.h>

dawgdic::DawgBuilder builder;
builder.Insert("apple", 0);
dawgdic::Dawg dawg;
builder.Finish(&dawg);
dawgdic::Dictionary dic;
dawgdic::DictionaryBuilder::Build(dawg, &dic);
bool hit = dic.Contains("apple");
```

## 适配说明

- 使用 Debian/Ubuntu 归档中的上游源码包和固定 SHA256，无第三方依赖。
- 使用 Conan 2 与 Autotools 构建。
- 配方执行上游完整 `make check`（4 个 Automake TESTS）。
- `test_package` 从消费者视角覆盖 C++ API 与两个打包工具。
- 未在本地冒充 OHOS AArch64 结果，最终平台结果以真机预检与赛事 CI 为准。

## 链接

- 原始上游（已归档）: http://code.google.com/p/dawgdic/
- 镜像: https://github.com/stil/dawgdic
- Debian 源码: https://deb.debian.org/debian/pool/main/d/dawgdic/
