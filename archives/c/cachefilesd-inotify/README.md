# cachefilesd-inotify

FS-Cache 用户态守护进程（inotify 版），cachefilesd 的 inotify 重写版（替代 dnotify）。
管理 FS-Cache 缓存文件与目录，供 NFS/AFS 等网络文件系统做本地持久化缓存。

- **Homepage**: https://gitlab.com/tomalok/cachefilesd-inotify
- **License**: GPL-2.0-or-later
- **Build system**: Makefile（C 项目，无 configure）

## OHOS 适配

C daemon，Makefile 构建。关键适配：传 `BUILDFOR=` 空跳过 Makefile 用 `file /usr/bin/make`
猜字长加 `-m32/-m64` 的逻辑（OHOS aarch64 clang 不认 -m64）；CC 从 conan conf 获取（R33）。

产物：`bin/cachefilesd` 可执行文件 + `res/cachefilesd.conf` 配置 + man pages。

### 运行期依赖（系统级，非 Conan）
- Linux 内核 `/proc/fs/cachefiles` 接口（FS-Cache 内核模块）
- xattrs（扩展属性）支持

## 版本
| 版本 | 状态 | 日期 |
|------|------|------|
| 0.11.1 | built | 2026-07-31 |
