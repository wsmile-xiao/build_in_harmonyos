# keepkey-agent

## 软件描述
keepkey-agent 是 [romanz/trezor-agent](https://github.com/romanz/trezor-agent) 生态的 KeepKey 硬件钱包 SSH/GPG agent 命令行工具——把 KeepKey 硬件钱包用作硬件级 SSH/GPG 认证密钥的 agent 进程。上游 pypi 包 `keepkey_agent` 0.9.0 是 1352 字节的壳包：`keepkey_agent.py` 仅 4 行（`ssh_agent = lambda: libagent.ssh.main(keepkey.KeepKey)`），实体逻辑在依赖闭包 `libagent`（trezor-agent 核心库：SSH/GPG agent 实现、设备抽象层、密钥格式处理）+ `keepkey`（KeepKey 官方 python 客户端：USB 通信、protobuf 协议、BIP32 密钥派生）中。

## 功能概述
- **SSH agent**：`keepkey-agent ssh://user@host` —— 用 KeepKey 设备上的 NIST256p/ED25519 密钥完成 SSH 认证（签名在硬件内，私钥不出设备）
- **GPG agent**：`keepkey-agent -s gpg://` 场景的 GPG 签名/解密代理
- **设备协议**：keepkeylib 的 protobuf wire 协议层（Initialize/GetFeatures/Ping/SignIdentity 等 40+ 消息类型）+ USB HID 传输
- **密钥格式**：SSH wire 格式公钥解析/导出（ecdsa-sha2-nistp256 / ssh-ed25519）、BIP32 地址派生、identity 字符串解析（ssh://user@host:port）

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无 C/C++ 编译。上游 sdist 壳 + 依赖闭包（libagent/keepkeylib/pure25519/ecdsa/semver/protobuf/mnemonic + ed25519 shim）全部从 OHOS pypi 镜像 vendor 纯 Python 组件，随包拷贝到 `lib/pythonX.Y/site-packages`
- 绕过 pip 构建（同 kegtron-ble 模式：环境 setuptools egg_info 加载 entry point 报 pbr 缺失实测）
- `bin/keepkey-agent` 入口脚本（console_scripts `keepkey-agent = keepkey_agent:ssh_agent` 的等价物）

### 关键攻坚点
1. **keepkeylib 0.7.3 py2 → py3 兼容**（2017 年代码）：4 处补丁——
   `unicode("x", "utf-8")` 默认值字面量 → `"x"`；`serialized_pb='...'` → bytes 字面量；`_ParseOptions(...)` 第二参数 → bytes；裸 `import types_pb2` → 包内相对导入（py3 全局 descriptor pool 下双模块实例 RegisterExtension 撞 `wire_in` 60002，实测必现）
2. **protobuf 版本锁定 3.15.4**：最后一个支持老式 descriptor 构造 API 的纯 `py2.py3` wheel 线（3.0.0 运行时用 `collections.MutableMapping` 在 py3.10+ 崩；4.x+ 删老 API；7.x 完全不兼容）
3. **ed25519 C 扩展替代**：上游依赖 C 扩展包 `ed25519`（OHOS 无签名 wheel 不可 dlopen）——写纯 Python API 兼容 shim，数学后端 `pure25519`（参考实现），RFC 8032 TEST 1 官方向量验证全过（pubkey 生成/签名/验证/篡改拒绝）
4. **hidapi（USB HID 传输层）边界**：`transport_hid.py import hid` 是按需导入——`keepkey-agent` 入口链（argparse → libagent.ssh.main）不触发；真实设备连接需另行提供 hidapi。这是硬件钱包工具的设备侧限制，如实申报
5. **Python 级依赖均未发布到 ohpcd conan 仓**：主配方不写 conan requires（PF4 依赖闸），全部 vendor 纯 Python 组件组装

### 与 Linux 的差异
- 无编译差异（纯 Python）
- USB HID 设备访问：`import hid`（hidapi C 扩展）在包内未提供——设备直连场景需消费者另行安装可用 hidapi；agent 的全部纯逻辑路径（密钥解析/签名验证/CLI/协议构造）不依赖它

## 依赖关系
| 依赖 | 版本 | 形态 | 用途 |
|------|------|------|------|
| libagent | 0.9.0（setup.py 锁定 >=） | sdist 纯 py | trezor-agent 核心库（SSH/GPG agent 实体） |
| keepkey | 0.7.3（setup.py 锁定 >=） | sdist 纯 py | KeepKey 官方客户端（keepkeylib） |
| ecdsa | 0.19.2 | wheel 纯 py | NIST256p 签名验证 |
| ed25519 | （shim 替代 1.4） | 纯 py shim | ED25519 验证（libagent 消费面） |
| pure25519 | 0.0.1 | sdist 纯 py | ed25519 纯 Python 数学后端 |
| semver | 3.1.0 | wheel 纯 py | 固件版本比较 |
| protobuf | 3.15.4 | wheel 纯 py | keepkeylib 协议消息层 |
| mnemonic | 0.21 | wheel 纯 py | BIP39 助记词（keepkey 依赖） |

> 以上均为 Python 级运行时依赖（pypi），未发布到 ohpcd conan 仓——已随包 vendor（纯 Python 组件 + py3 兼容补丁 + ed25519 shim）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.9.0 | built | 2026-09-19 | 纯 Python noarch 适配；上游无测试（N=0 如实申报），功能实测 7/7 PASS |

## 参考资料
- 上游仓库: https://github.com/romanz/trezor-agent（v0.9.0 tag：a5897ae2d46be9fe771b3188669e5d0920b848c7）
- PyPI: https://pypi.org/project/keepkey_agent/0.9.0/
- KeepKey python 客户端: https://github.com/keepkey/python-keepkey
