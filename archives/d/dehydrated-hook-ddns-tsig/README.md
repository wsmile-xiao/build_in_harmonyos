# dehydrated-hook-ddns-tsig

dehydrated（ACME/Let's Encrypt 客户端）的 DNS-01 challenge hook：纯 Python
脚本，调用 dnspython 以 RFC2136 动态 DNS 更新（TSIG 签名）向授权服务器
发布/清理 `_acme-challenge` TXT 记录，并通过 DNS 查询验证传播。

## 功能概述

- `deploy_challenge` / `clean_challenge`：发布与删除 ACME DNS-01 TXT 挑战
- TSIG 密钥认证（hmac-md5/sha1/sha224/sha256/sha384/sha512）
- 传播验证：逐 NS 查询 TXT 是否生效/清除
- 链式 hook：一条命令可携带多组 domain/token；支持 `dns_rewrite` sed 变换

## OHOS 适配

- 纯 Python 单脚本，无编译；shebang 修正为 `#!/usr/bin/env python3`
  （设备无 `python` 命令），脚本装至 `bin/dehydrated-hook-ddns-tsig`。
- 设备 Python 3.12 无 dnspython 且 OHOS 归档无配方：本包 vendor
  dnspython 2.8.0（纯 Python，MIT）至 `lib/python3.12/site-packages/`，
  入口脚本以相对 sys.path 引导加载。
- 补丁修复：dnspython 2.x 兼容（rcode `==` 比较、`resolver.resolve`）、
  key_* 未初始化 NameError、nameserver 缺记录容错、ISC key 文件解析
  py3 兼容（参照 Debian 0.1.4-8 的移植经验）。
- 可选依赖 iscpy（读 ISC/rndc key 文件）为 py2-only，不打包；请在 conf
  中直接配置 `key_name` / `key_secret` 规避。
- 已知上游 bug：`request_failure`/`startup_hook`/`exit_hook` 因
  `read_config()` 缺 domain 参数会崩溃；`--help`、`invalid_challenge`、
  `deploy_cert`、`unchanged_cert` 可正常离线运行。

## 依赖关系

- 运行：Python 3.8+；dnspython 2.8.0（已 vendor，见版本级 conanfile.py，
  URL+SHA256 固定）
- 调用方：dehydrated（hooks 目录指向本脚本）
- 网络：运行时需 UDP/53 到配置的 name_server_ip（离线仅 --help/no-op 可用）

## 参考资料

- 上游仓库：https://github.com/eferdman/dehydrated-hook-ddns-tsig
- 版本归档：https://github.com/eferdman/dehydrated-hook-ddns-tsig/archive/refs/tags/v0.1.4.tar.gz
- 打包参考：Debian `dehydrated-hook-ddns-tsig` 0.1.4-8
- 依赖：https://pypi.org/project/dnspython/2.8.0/
