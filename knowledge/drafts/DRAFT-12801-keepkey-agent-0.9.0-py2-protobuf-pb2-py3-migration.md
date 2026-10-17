# E-draft: py2 时代 protobuf pb2 模块在 Python 3 的五补丁迁移配方 + protobuf 运行时版本决策树

- **id**: keepkey-agent-0.9.0-py2-protobuf-pb2-py3-migration
- **severity**: 2
- **category**: compat|python|runtime
- **phase**: runtime
- **来源软件**: keepkey-agent 0.9.0（vendored 闭包：libagent 0.9.0 + keepkey 0.7.3 keepkeylib）
- **验证门**: conan create（ohos-aarch64，OHOS Python 3.12.9）+ build 功能实测 7/7 + test_package 4/4

## 现象（error_signature 可机器匹配）

vendor 2016-2017 年代 python 包的 `*_pb2.py` 后，在 Python 3 上依次踩到：

| # | 报错 | 根因 |
|---|------|------|
| 1 | `NameError: name 'unicode' is not defined` | py2 `unicode("x","utf-8")` 默认值字面量；**注意** `unicode = str` shim 不够——`str("x","utf-8")` 报 `TypeError: decoding str is not supported`，必须替换调用形式本身 |
| 2 | `memoryview: a bytes-like object is required, not 'str'` | `serialized_pb='...'` py2 str 字面量是 bytes 语义，py3 要 `b` 前缀 |
| 3 | 同上（`_ParseOptions` 内部） | `_ParseOptions(xxx(), '...')` 第二参数同样要 bytes（keepkey 115+ 处） |
| 4 | `AssertionError: Extensions "wire_in" and "wire_in" both try to extend message type "google.protobuf.EnumValueOptions" with field number 60002` | 裸 `import types_pb2` 在 py3 下解析出**两个模块实例**（裸名 vs 包名），各自对**全局 descriptor pool** 执行 RegisterExtension 撞号 |
| 5 | `TypeError: Ping() takes no arguments` / 裸 `NotImplementedError`（SerializeToString） | py2 类属性 `__metaclass__ = _reflection.GeneratedProtocolMessageType` 在 py3 被**静默忽略**——消息类从未被协议化 |

## protobuf 运行时版本决策树（老 pb2 专用）

```
pb2 由 protoc <3.5 生成（serialized_pb 是 str 字面量）
├─ protobuf 7.x —— 老式 descriptor 构造 API 已删（AttributeError）→ ✗
├─ protobuf 3.0.0 —— 运行时 containers.py 用 collections.MutableMapping（py3.10+ 移除）→ ✗
└─ protobuf 3.15.4 —— 老构造 API 还在 + py3 运行时干净 + 纯 py2.py3-none-any wheel → ✅
```

## 修复方案（五补丁，regex 固化，幂等）

```python
import re
# 1. unicode("x", "utf-8") -> "x"（禁用 unicode=str shim）
src = re.sub(r'unicode\("((?:[^"\\]|\\.)*)", "utf-8"\)', r'"\1"', src)
# 2. serialized_pb=' -> serialized_pb=b'
src = src.replace("serialized_pb='", "serialized_pb=b'")
# 3. _ParseOptions 第二参数 -> bytes
src = re.sub(r"(_ParseOptions\(\s*\w+\.\w+\(\),\s*)'", r"\1b'", src)
# 4. 裸 import types_pb2 -> try 包内相对导入（防双实例撞全局池）
old = "import types_pb2\n"
new = ("try:\n    from . import types_pb2\n"
       "except ImportError:\n    import types_pb2\n")
# 5. py2 metaclass 类属性 -> py3 六参数语法（每个消息类）
src = re.sub(
    r"class (\w+)\(_message\.Message\):\n"
    r"  __metaclass__ = _reflection\.GeneratedProtocolMessageType",
    r"class \1(_message.Message,\n"
    r"             metaclass=_reflection.GeneratedProtocolMessageType):",
    src)
```

## 验证方式（设备无关全覆盖）

迁移后闭包跑功能实测：导入链（壳包→libagent→keepkeylib）→ CLI argparse 入口 →
protobuf Ping 消息 wire 序列化往返 → NIST256p/ED25519 双曲线签名验证闭环
（`libagent.formats.parse_pubkey` + 设备风格 raw r||s 签名）。

## fallback

补丁不可接受时（法务冻结 vendor 树/文件过多）：用现代 protoc 从上游 .proto
重新生成 pb2 模块（需要上游仓库的 .proto 定义）。

## 适用面

trezor/keepkey/2016-2017 py2 protobuf 生态（早期 bitcoin/ethereum 工具链）
及一切 vendor 老 pb2 的 python noarch conan 适配场景。知识图谱查重零命中
（E143 shebang / E219 沙箱 python / E269 py2 脚本 / E319 nltk noarch /
E226 subprocess bytes 均不覆盖 protobuf pb2 迁移）。
