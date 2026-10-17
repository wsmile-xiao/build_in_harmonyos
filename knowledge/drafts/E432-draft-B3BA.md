# E432 — OHOS sysroot 缺 fts.h / libfts：递归目录遍历编译失败

## 错误特征
- `fatal error: 'fts.h' file not found`
- 符号: fts_open / fts_read / fts_close

## 触发条件
- 平台: OHOS musl 系 sysroot
- 阶段: compilation
- 典型代码: 直接调用 fts(3) API 做递归目录遍历的软件

## 根因分析
OHOS musl 系 sysroot 无 fts(3) 目录遍历 API 与 libfts；zeek 的 auxil/libunistd 内嵌 fts
是 macOS 专属路径，不参与 Linux 构建，无树内兜底。

## 解决方案

### 推荐方案
用 C++17 `std::filesystem::recursive_directory_iterator` 重写遍历函数（可移植、无平台宏），
`#include <fts.h>` 同步改 `<filesystem>`。zeekygen Target.cc 的 dir_contents_recursive 实测通过。

## 验证
```bash
ls <sysroot>/usr/include/fts.h      # 不存在 = 命中
find <sysroot> -name 'libfts*'      # 无 = 命中
make zeekygen                        # 编译通过 = 修复验证
```

## 关联条目
- 同来源: PR #11976（zeek 8.2.1，zeekygen）
