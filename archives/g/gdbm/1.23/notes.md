# gdbm 1.23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-12
- 编译器: clang 15.0.4
- 状态: success

## 编译步骤
1. 下载源码 gdbm-1.23.tar.gz 并解压
2. 创建 orig/work/verify 三目录
3. 应用 config.guess/config.sub 补丁
4. `./configure --prefix=$PREFIX --enable-libgdbm-compat --disable-nls CFLAGS="-fPIC"`
5. `make -j$(nproc) && make install`
6. 修复符号链接：`ln -sf libgdbm.so.6.0.0 libgdbm.so` 等

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libintl 链接失败（undefined symbol: libintl_gettext） | 默认启用 NLS | `--disable-nls` 禁用国际化 |
| 2 | 共享库加载失败 | 动态链接器找不到路径 | 设置 LD_LIBRARY_PATH 或使用静态库 |
| 3 | config.guess 不识别 HarmonyOS | 标准问题 | 添加 HarmonyOS 检测 case |
| 4 | gdbm_open 不能用 /tmp 路径 | HMDFS 限制 | 使用 $TMPDIR |

## 依赖版本
- 无必须依赖
- 可选：readline

## 验证结果
```bash
# gdbm_open + store 3条 + fetch验证 + 遍历key 全通过 ✅
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| gdbm-1.23-ohos-aarch64.tar.gz | 1.3MB | 主包 |

## 注意事项
- 必须使用 `-fPIC`（静态库被链接到共享库时必需）
- `--enable-libgdbm-compat` 提供 dbm/ndbm 兼容接口，Python 的 _gdbm 模块需要
---

**编译结束**: 2026-08-06 12:44
**最终状态**: built
