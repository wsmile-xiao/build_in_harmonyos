# libimobiledevice 1.4.0 适配笔记

## 与 1.3.0 的差异（已在制品仓的 sibling）

- **结构**：`common/` 只剩 `debug.c/h` + `userpref.c/h`，utils/socket/thread/
  log 全部移入 **libimobiledevice-glue**（新硬依赖 `>= 1.3.0`，仓里有 1.3.0）。
- **新增硬依赖 libtatsu >= 1.0.3**（Apple TSS 客户端，仓里有 1.0.5；它依赖
  libcurl/8.5.0，共享库，运行时由 conanrun 注入 LD_LIBRARY_PATH）。
- **SSL**：configure 默认 `use_openssl=yes`（`PKG_CHECK openssl >= 0.9.8`），
  不再需要 1.3.0 的 `--enable-openssl`；openssl/1.1.1w 直连。
- **1.3.0 的 `enum plist_format_t` 补丁不再需要**：那段代码已随 utils 移走。

## OHOS 坑（全部复用已进图谱的 E 条目，路径 A）

| 坑 | 处理 | 图谱/先例 |
|---|---|---|
| autoconf AS_TMPDIR `umask 077 && mktemp -d` 在 HMDFS 上权限坏，config.status 写不进 subs*.awk | 假 mktemp 包装（exit 1）迫使 mkdir 回退 | E114，glue/libtatsu/1.3.0 同款 |
| 自带 configure 内 `umask 077` | `replace_in_file` 改 022 | E011 族，1.3.0 同款 |
| config.guess 不认 OHOS | `--build=aarch64-unknown-linux-gnu` | E114 族，全生态先例 |
| 依赖包装的 .la `libdir='//lib'` 无效，libtool 报 not a valid libtool archive | generate() 里把依赖 `*.la` 改名 `.bak` | 1.3.0 同款 |
| **tools 用 libplist 2.6.0 API**（`plist_dict_get_uint`/`plist_dict_copy_uint`/`PLIST_OPT_NONE`）而 configure.ac 只要求 >= 2.3.0 | 补丁 0001：逐字 backport libplist 2.6.0 实现为 static inline（LGPL-2.1+） | libtatsu/1.0.5 已合入 0001 同族同法 |
| CMakeDeps 不给「声明 libs 的聚合 target」传播依赖 usage requirements | test_package 显式 require + link 全部静态闭包 | — |
| HMDFS 上并行 make jobserver fifo EPERM | `make -j1` | R9 |
| Cython/Python 绑定 | `--without-cython` | — |

## 验证

- 上游无测试套件（无 tests/、无 check 程序）→ N=0，补全口径。
- 消费者 `test.c`：链接静态库 + 全部传递依赖后调公开 API——
  `idevice_get_device_list`（无守护时走文档化错误路径）、`idevice_new` 假
  UDID 必须干净失败、`idevice_set_debug_level` 可调；3 断言全过。
- 产物：`lib/libimobiledevice-1.0.a` + 26 个头 + `bin/` 下 20 个 idevice*
  工具（静态链接）。
