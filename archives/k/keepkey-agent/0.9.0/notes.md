# keepkey-agent 0.9.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无 C/C++ 编译）
- **编译日期**: 2026-09-19
- **平台**: OHOS PC（arm64）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/k/keepkey-agent/0.9.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（keepkey_agent-0.9.0.tar.gz，1352B，
sha256=47c85de0...），`strip_root=True` 解压。sdist 内容：
setup.py / keepkey_agent.py（4 行壳）/ PKG-INFO / egg-info。

### 2. 形态定性（W0 实测）
- **keepkey-agent 0.9.0 = 壳包**：`keepkey_agent.py` 全部 4 行：
  ```python
  import libagent.gpg
  import libagent.ssh
  from libagent.device import keepkey
  ssh_agent = lambda: libagent.ssh.main(keepkey.KeepKey)
  ```
- 实体逻辑在 `libagent` 0.9.0（25.8KB sdist，纯 py：ssh/gpg agent、
  device 抽象、formats 密钥处理）+ `keepkey` 0.7.3（80KB sdist，
  keepkeylib 纯 py：protobuf 协议、BIP32、USB 传输）
- **依赖链 C 扩展评估**：`keepkey` 声明 `hidapi==0.7.99.post15`
  （cython C 扩展——USB HID 传输层）；`libagent` 声明 `ed25519>=1.4`
  （C 扩展）。两者均**不可纯拷贝**——ed25519 用纯 py shim 替代闭环；
  hidapi 是设备直连才触发的按需导入（transport_hid.py），入口链不碰
- pypi 元数据 requires_dist=null（老 setup.py 时代元数据），依赖从
  sdist 的 setup.py install_requires 读取：`libagent>=0.9.0` +
  `keepkey>=0.7.3`

### 3. py2 → py3 攻坚（keepkeylib 0.7.3，2017 年代码）
在 OHOS Python 3.12.9 上逐个实测修复：
1. `types_pb2.py`/`messages_pb2.py`：`unicode("", "utf-8")` 默认值
   字面量（38+8 处）→ `""` / `"Bitcoin"` 等（py3 的 unicode=str 会让
   str("","utf-8") 直接 TypeError）
2. `serialized_pb='...'` → `serialized_pb=b'...'`（protobuf
   FileDescriptor py3 要求 bytes）
3. `_ParseOptions(descriptor_pb2.XxxOptions(), '...')` 第二参数 →
   b 前缀（116 处）
4. **裸 `import types_pb2` → try 相对导入**（最隐蔽）：py3 下裸名
   `types_pb2` 与包名 `keepkeylib.types_pb2` 是两个模块实例，各自执行
   `RegisterExtension(wire_in)` 在全局 descriptor pool 撞
   `AssertionError: Extensions "wire_in" and "wire_in" both try to
   extend message type "google.protobuf.EnumValueOptions" with field
   number 60002`

**protobuf 版本选型**（实测排除法）：
- 7.36.2：`_AddSerializedProto`/老 descriptor 构造 API 已删——崩
- 3.0.0：运行时 `containers.py` 用 `collections.MutableMapping`
  （py3.10 移除）——崩
- **3.15.4 ✅**：老 descriptor API 还在 + py3 运行时干净 + 纯
  `py2.py3-none-any` wheel

### 4. ed25519 C 扩展替代（纯 Python shim）
libagent/formats.py 的消费面（grep 实测）：`ed25519.VerifyingKey` /
`ed25519.keys.VerifyingKey` / `BadSignatureError`。写 API 兼容 shim
（ed25519.py），数学后端 pure25519 0.0.1（纯 Python 参考实现）。
**RFC 8032 TEST 1 官方向量验证**：pubkey 生成 ✓ 签名 ✓ 验证 ✓
篡改拒绝 ✓。

### 5. hidapi（USB HID）边界——如实申报
`keepkeylib/transport_hid.py` 顶层 `import hid`——但它是**按需传输
后端**：`keepkey_agent.ssh_agent()` 入口链（argparse → libagent.ssh.main
→ device 抽象）只在实际连接设备时才触发 transport 构造。CI 无硬件
设备，导入链与全部纯逻辑路径（CLI/协议/签名验证）不触碰 hid。
**设备直连场景**需消费者另行提供可用 hidapi（OHOS 无签名 wheel）。

### 6. 功能实测（build()——rule 4 如实申报）
上游 0.9.0 **无测试文件**（N=0）：
- sdist 1352B 无 tests/
- romanz/trezor-agent v0.9.0 tag 的 keepkey_agent/ 子目录同样只有
  keepkey_agent.py 与 setup.py
- keepkey 0.7.3 有 34 个测试文件，但 tests/common.py 的 KeepKeyTest
  .setUp() 直接构造 HidTransport + DebugLinkTransport 枚举真实
  KeepKey USB 设备并 wipe_device——**全部硬件依赖，CI 无设备，逐项豁免**

设备无关的实体逻辑用功能实测覆盖（7 项断言组）：
1. 完整导入链（keepkey_agent → libagent(.ssh/.gpg/.device.keepkey)
   → keepkeylib）
2. CLI 入口 argparse 全链（usage 输出）
3. protobuf Ping 消息 wire 序列化往返
4. NIST256p SSH 签名验证闭环（KeepKey 主曲线：parse_pubkey →
   设备风格 raw r||s 签名 → verifier → SSH wire 签名 74B）
5. ED25519 签名验证闭环（shim + pure25519，含篡改签名拒绝）
6. ed25519 shim 数学正确性（RFC 8032 官方向量）
7. ssh:// identity 字符串解析

**实测结果：7/7 PASS**

## 依赖处理

全部 Python 级依赖未发布到 ohpcd conan 仓（`conan download <pkg>
-r=ohpcd --only-recipe` 实测 404/空）——不写 conan requires（PF4
依赖闸），从 OHOS pypi 镜像 vendor：

| 组件 | 版本 | 来源形态 |
|------|------|---------|
| libagent | 0.9.0 | sdist（tar.gz，取 libagent/ 包目录） |
| keepkey | 0.7.3 | sdist（取 keepkeylib/ 包目录） |
| pure25519 | 0.0.1 | sdist（取 pure25519/ 包目录） |
| ecdsa | 0.19.2 | wheel |
| semver | 3.1.0 | wheel |
| protobuf | 3.15.4 | wheel（py2.py3-none-any 纯 py） |
| mnemonic | 0.21 | wheel |

vendor 组件打 py3 兼容补丁 + ed25519 shim 后随包分发到
site-packages——消费者 `import keepkey_agent` 即全链可用。

## 上游测试申报（rule 4）

| 项 | 值 |
|---|---|
| 上游注册测试数 N | **0**（keepkey-agent 0.9.0 sdist 无 tests/——1352B 壳包） |
| 本地实测 | 功能实测 7/7 PASS（设备无关逻辑全覆盖） |
| 跳过/失败 | keepkey 0.7.3 的 34 个测试全依赖真实 KeepKey USB 设备——硬件依赖逐项豁免 |
| 硬件依赖 | USB HID（hidapi）——入口链不触发，设备直连场景需消费者另行提供 |

## test_package（R34 消费验证）

`test_keepkey_agent.py`：
1. HARD 文件存在（keepkey_agent.py + 11 组件运行时闭包）
2. `bin/keepkey-agent --help` 实跑（argparse 全链）
3. 导入链 + protobuf wire 往返 + NIST256/ED25519 双曲线签名验证闭环
   （4 项断言组，子进程隔离）

## 版本边界说明
- keepkey_agent.py 的 GPG 路径（libagent.gpg）随导入链验证
- `libagent.device.keepkey.KeepKey.required_version == ">=1.0.4"`
  （上游固件版本约束断言）
- pypi home 指向 romanz/trezor-agent（keepkey-agent 是其 KeepKey
  变体发行物）
