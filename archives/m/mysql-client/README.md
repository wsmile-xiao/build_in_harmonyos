# MySQL Client

MySQL 客户端库和工具集，提供 mysqladmin、mysqldump、mysqlcheck 等数据库管理工具及 libmysqlclient 客户端连接库。

## 编译指导

在 HarmonyOS/OpenClaw 平台编译时需使用 cmake 配置：
```bash
cmake -DWITHOUT_SERVER=ON \
      -DWITH_EDITLINE=none \
      -DWITH_SSL=system \
      -DWITH_LIBEVENT=bundled \
      -DFORCE_UNSUPPORTED_COMPILER=ON \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      ..
make -j$(nproc)
```

关键注意事项：
- `WITH_EDITLINE=none` 必须设置（HarmonyOS NEXT 无 editline/libedit）
- 编译完成后需使用 `binary-sign-tool` 签名所有 ELF 二进制
- mysql CLI 交互工具不可用（依赖 editline），其他客户端工具正常

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| [8.4.9](./8.4.9/) | ✅ published | 2026-06-09 | 8个补丁，成功编译 |
| [8.0.46](./8.0.46/) | ❌ failed | 2026-06-09 | 源码包不完整，缺少核心目录 |