# aide — Advanced Intrusion Detection Environment

## 一句话说明
AIDE 是文件完整性监控工具，Tripwire 的自由替代品：监控文件属性（权限/inode/用户/组/大小/mtime 等）与多种哈希，检测未授权的文件变更。

## 功能概述
- 文件属性监控：permissions、inode、user、group、size、mtime、atime、ctime、links、growing size
- 多哈希支持：md5/sha1/rmd160/sha256/sha512/stribog/sha3 等
- 明文配置文件与数据库，支持规则/变量/宏
- 正则表达式选择监控文件（PCRE2）
- gzip 数据库压缩（zlib）

## OHOS 适配
- **config.guess/config.sub 补丁**（E007）：config.guess 不识 HarmonyOS（uname -s=HarmonyOS），需补 __OHOS__ 检测与 ohos-linux 三元组，禁止用 --build/--host 绕过（会误判交叉编译导致运行时检测全部跳过）。
- **HMDFS umask 077 问题**（E081 同类）：configure 生成 config.status 时 `umask 077 && mktemp -d` 创建的临时目录在 HMDFS 上无法写入，需将 configure 中 umask 077 改为 022。
- **NLS**：鸿蒙无 libintl（E027），configure 时禁用 locale 相关；aide 0.19.3 不强制依赖 gettext。
- **加密后端**：上游支持 libnettle 或 libgcrypt 二选一；nettle 尚未发布到 ohpcd 制品仓，本配方用 libgcrypt/1.11.0。
- **链接**：libgcrypt 在 ohpcd 仅发布 shared 包，aide 采用动态链接（R26 针对系统同名库，aide 非系统同名库）。
- **check 库测试**：make check 需要 libcheck（check/0.15.2 已发布），运行需设置 TEMP/TMPDIR 到可写目录（P_tmpdir 默认 /tmp 只读）。

## 依赖关系
- 编译依赖：pcre2/10.45（必需）、libgcrypt/1.11.0（+libgpg-error 传递）、zlib/1.3.1（gzip 压缩）、check/0.15.2（测试）
- 运行依赖：libgcrypt.so/libgpg-error.so（动态链接，由 Conan 管理）

## 参考资料
- 上游仓库：https://github.com/aide/aide
- 文档：https://aide.github.io
- 版本：0.19.3（2026-01-31 发布）
