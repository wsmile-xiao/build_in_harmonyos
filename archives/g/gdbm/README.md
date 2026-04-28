# gdbm

## 简介
GDBM (GNU DataBase Manager) — 轻量级键值对数据库库，使用可扩展哈希算法实现。Python 3.9 的 `_gdbm` 模块依赖此库。

## OHOS 适配
- 标准 autotools，打 config.guess/config.sub 补丁即可编译
- 推荐 `--disable-nls` 避免 libintl 依赖问题
- 必须使用 `-fPIC`（静态库链接到共享库时必需）
- `gdbm_open` 路径不能使用 `/tmp`（HMDFS 限制），需用 `$TMPDIR`
- `--enable-libgdbm-compat` 提供 dbm/ndbm 兼容接口

## 依赖
- 编译依赖：无必须依赖
- 可选依赖：readline

## 功能验证
```bash
# 验证库安装
ls -la $HOME/usr/local/lib/libgdbm*
pkg-config --modversion gdbm
```

## 参考
- 官方手册：https://www.gnu.org/software/gdbm/manual/
