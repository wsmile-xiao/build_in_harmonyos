# pianod（上游发布包名 pianod2）

> 本仓库归档标识为 **pianod**（任务书指定名，且与安装出的二进制 `bin/pianod` 一致）；
> 上游 r421 的发布包/`AC_INIT` 名称是 **pianod2**（`pianod` 是该项目的初代产品名）。两者指同一软件。

**多源、可网络控制的音乐播放守护进程**（MIT，Devious Fish）

pianod2 把一台机器变成中央音乐服务器：本地曲库 + 多个 Pandora 账号混合播放，
通过 Web 客户端、行协议或 JSON/WebSocket 远程控制，也可用脚本调度。

## 鸿蒙 PC 适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [420](420/) | built | r420（2025-12-28）沿用 421 适配（4 补丁逐字节复用、`git apply --check` 验证）；gstreamer 引擎 + OpenSSL TLS |
| [421](421/) | built | r421（2026-02-03）首次适配；gstreamer 引擎 + OpenSSL TLS |

## 构建组成（本配方选定）

```
--with-engine=gstreamer     # 媒体引擎（自带音频输出，无需 libao/libsdl）
--with-tls=openssl          # TLS（football 内置 OpenSSL 传输层）
--with-pandora              # 需要带 TLS 的 curl（用 curl/8.15.0.1，非 libcurl/8.5.0）
--with-compression          # zlib 数据文件压缩
--with-taglib               # 本地曲库 ID3 元数据
```

自动降级项：access control（无 libwrap）、password shadowing 走 passwd 模式（无 PAM）。

## 用法

```bash
# 必须先给出 Web 客户端目录：包内 prefix 为 "/"，编译期固化的 //share/pianod/html 不可用，
# 不传 -c 时 daemon 会 "Unable to create service, giving up"（真机实测）。
# conan 的 run 环境已导出 PIANOD_CLIENTDIR 指向包内实际路径：
source conanrun.sh                       # 由 conan install 生成，含 PATH 与 PIANOD_CLIENTDIR
pianod -d ~/.config/pianod2 -c "$PIANOD_CLIENTDIR" -p 4445 -P 4446 -s 0
# 浏览器打开 http://<host>:4446/pianod/  使用内置 Web 客户端
pianod -v -v                             # 查看编译进二进制的依赖与版本（curl/OpenSSL/gstreamer/taglib）
```

| 命令 | 说明 |
|------|------|
| `pianod` | 守护进程（C++ 原生，已在 OHOS 验证） |
| `piano` | 命令行客户端 — **AT&T ksh93 脚本，OHOS 无 ksh93，暂不可用** |
| `runmix` | 定时排程工具 — 同上 |

## 已知限制

1. `piano`/`runmix` 依赖 ksh93 的 `getopts`/`print`/`whence` 内建，OHOS 生态未提供 ksh93
   （cmd-pkgs 仅有 dash、zsh）；请用 Web 客户端或 4445 端口行协议替代。
2. 上游端到端测试 `pianod_unittest` 同样是 ksh93 脚本，按上游自带守卫上报 SKIP(exit 77)。
3. 播放 Pandora 需有效账号（`PANDORA_USER`/`PANDORA_PASSWORD`）。
4. 音频输出走 gstreamer，需要设备上存在可用的 sink 插件与音频设备权限。

## 上游

- 主页：https://deviousfish.com/pianod
- 发布源（SVN 项目，无 Git 镜像）：https://deviousfish.com/Downloads/pianod2/
- 邮件列表：pianod@lists.deviousfish.com
