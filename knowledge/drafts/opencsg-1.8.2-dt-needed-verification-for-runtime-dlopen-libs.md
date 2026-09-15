# 用 DT_NEEDED 验证运行时 dlopen 型库未误链系统同名库（R26 自查方法）

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs.kv` 成对。

## 适用场景

库在**运行时**才 `dlopen` 解析依赖（自带 glad/glew、插件/驱动式加载器、延迟绑定图形或多
媒体库）。此类库的产物**不应**硬链接这些依赖。若构建过程意外把系统同名库（如
`libGL` / `libEGL` / `libGLESv2`）链进产物：

- 与它自己声明的"运行时加载"策略矛盾；
- 安装后可能与系统库争抢加载（R26 类风险）。

**仅凭"编译通过"发现不了**，必须检查产物的动态依赖表。

## 断言方法

```bash
# 1) 动态依赖表恰好是预期集合，且不含应交由运行时 dlopen 的库
llvm-readelf -d <pkg>/lib/lib<name>.so | grep -iE "NEEDED|SONAME"

# 2) 加载器名字确实进了产物（证明加载逻辑被编译进来）
llvm-strings <pkg>/lib/lib<name>.so | grep -E "libGL|libEGL"

# 3) 导出符号数量/关键符号符合预期
llvm-nm -D --defined-only <pkg>/lib/lib<name>.so | wc -l
```

把这三项结果写进 `notes.md` / PR 的"产物验证"小节，作为可复查的适配正确性证据。

## 证据（opencsg 1.8.2）

| 检查 | 设备 `conan create` | 本机 OHOS SDK 交叉编译 |
|------|--------------------|----------------------|
| `DT_NEEDED` | `[libc++_shared.so, libc.so]` | `[libc++_shared.so, libc.so]` |
| 是否含 `libGL*`/`libEGL*` | 否 | 否 |
| 加载器字符串 | 含 `libGLv4.so`/`libEGL.so` | 同 |
| 导出 OpenCSG 符号 | 885 | 885 |

GL 入口点由自带 glad 在 `render()` 里 `dlopen` 解析，因此产物无 GL 链接依赖——这正是预期。
该检查同时充当 R26 自查：确认没有把系统同名/图形库硬链进产物。
