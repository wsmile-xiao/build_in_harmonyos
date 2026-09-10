# dehydrated-hook-ddns-tsig 0.1.4 适配笔记

## 软件概述

dehydrated（ACME/Let's Encrypt 客户端）的 DNS-01 challenge hook：纯 Python
单脚本（874 行），用 dnspython API 做 RFC2136 动态 DNS 更新（TSIG 签名）
并查询验证 TXT 记录。上游 v0.1.4（2018-07-11）即 master 最终状态——
上游已停更，所有现代兼容修复必须以 recipe patches 携带。

- 上游归档（conandata.yml 固定）仅 4 个文件：COPYING / README.md /
  dehydrated-hook-ddns-tsig.conf / dehydrated-hook-ddns-tsig.py。
- 无构建系统、无测试套件、无 CI（test_package 为本 recipe 自建）。
- License: GPL-3.0-or-later（COPYING 仅声明头）。

## 依赖闭包（关键决策）

- **dnspython（必需）**：设备 Python 3.12.9 无 dnspython 模块；
  ConanCenter 无 dnspython 配方；本仓 archives/ 亦无 → 闭包缺口。
  解决方式：**vendor 进本包** —— source() 以固定 URL+SHA256 拉取
  官方 PyPI sdist dnspython-2.8.0（纯 Python，MIT，无二级依赖），
  装入 `lib/python3.12/site-packages/dns/`；入口脚本经 patch 0001 的
  相对路径 sys.path 引导加载（不写绝对路径）。
  注意：dnspython URL/SHA256 固定在 conanfile.py（而非 conandata.yml），
  因为 CI 的 mirror-fallback/predl 会原地改写 conandata.yml 中的任意
  URL 字段为镜像/file:// 形式，conanfile 不受影响。
- **iscpy（上游可选依赖，不打包）**：仅当用 DDNS_HOOK_KEY_FILE 环境变量
  从 ISC/rndc key 文件读配置时才 import；iscpy 本身 py2-only
  （'rU' 打开模式、keys()[0] 下标），且 archives/ 无配方。
  规避方式：conf 直接配 key_name/key_secret（不触发 iscpy 路径）。
  patch 0006 仍修复了脚本侧该路径的 py3 兼容问题（若未来接入
  py3 兼容的 iscpy 即可工作）。
- dehydrated 本体是调用方而非本包依赖（另有 dehydrated-0.7.2 run）。

## 补丁集（参照 Debian 0.1.4-8 的移植经验 + 自查修复）

| 补丁 | 内容 | 来源 |
|---|---|---|
| 0001-ohos-python3-entry | shebang `python`→`python3`（设备无 `python`）；追加相对路径 sys.path 引导 vendored dnspython | Debian python3.patch + OHOS 打包 |
| 0002-init-key-variables | ensure_config_dns 预初始化 key_name/key_secret/key_algorithm，防部分配置下 NameError | Debian key_algorithm.patch |
| 0003-rcode-value-comparison | 2 处 `rcode is dns.rcode.NOERROR` → `==`（dnspython 2.x IntEnum 身份比较恒 False，update 永远被判失败） | Debian rcode_compare.patch |
| 0004-dnspython-2x-resolve | 4 处 `dns.resolver.query` → `.resolve`（query 自 2.0 弃用） | Debian deprecated_dns-resolver-query.patch |
| 0005-nameserver-tolerance | query_NS_record 中单个 nameserver 缺 A/AAAA 记录不再丢弃其余 NS（内层 try）；verify_record 回退路径 nameserver 裸字符串包成列表（dnspython 2.x setter 拒绝 str） | Debian 0002 精神 + 自查 |
| 0006-py3-key-file-compat | ISC key 文件路径 py3 修复：open 'rU'→'r'、keys()[0]/values()[0] → list(...)[0] | 自查（上游带病） |

## 上游 bug 备忘（未打补丁，避免改变行为）

- `startup_hook`/`exit_hook` 误调 `post_hook('request_failure', ...)`
  （应为各自的 post_startup_hook/post_exit_hook）— 无害，仅 post hook 名不对。
- `read_config()` 对无 `domain` 参数的 hook（request_failure /
  startup_hook / exit_hook）会 `res['domain']` KeyError 崩溃 —
  上游 bug；因此离线冒烟只能选含 domain 的 no-op hook
  `invalid_challenge`。

## 安装布局与运行

```
<pkg>/bin/dehydrated-hook-ddns-tsig          # 0755, #!/usr/bin/env python3
<pkg>/lib/python3.12/site-packages/dns/      # vendored dnspython 2.8.0
<pkg>/share/doc/dehydrated-hook-ddns-tsig/dehydrated-hook-ddns-tsig.conf
```

- 配置搜索路径：/etc/dehydrated/...、/usr/local/etc/dehydrated/...、
  ./dehydrated-hook-ddns-tsig.conf；设备上建议直接 `-c FILE` 指定。
- 运行时功能依赖到 name_server_ip 的 UDP/53 出网；无网时所有
  deploy/clean challenge 会失败（属预期），`--help` 与 no-op hook
  （invalid_challenge 等，注意上面的 domain KeyError 例外）可离线验证。

## test_package 设计（上游无测试，自建 L1）

`verify_hook.py` 从消费者侧验证（满足 R34/L1e 破坏性反证——产物被移走
即失败）：
1. 安装布局：bin 脚本存在且可执行、shebang 为 python3、conf 样例就位；
2. vendored dnspython 生效：sys.path 前插包内 site-packages，
   断言 `dns.__file__` 在包内、版本 2.8.0，完整导入 hook 所需 API 链
   （resolver/tsig/tsigkeyring/update/query/exception/rcode/rdata/rdatatype）；
3. 离线 API 行为：rcode== 语义（0 == NOERROR 且恒等比较确实不成立）、
   TSIG keyring + Update 构造 + to_wire()、Resolver.nameservers 列表赋值；
4. 入口冒烟：`--help` 退出 0；`invalid_challenge example.com <resp>`
   完整走 argparse → configparser → 回调分发 → 退出 0（无网络）。

## OHOS 适配要点

- 纯 Python 无编译；build() 仅 `python3 -m py_compile` 语法验证。
- 域名差异：无；不依赖 curl/dig/nsupdate/openssl 二进制。
- 设备文件系统大小写不敏感：包内无同名不同.case 文件，安全。
