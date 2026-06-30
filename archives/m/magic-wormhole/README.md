# magic-wormhole

## 简介
Magic Wormhole 是一个安全的文件/消息传输工具, 通过短代码(nameplate+code)在两台计算机之间建立加密连接, 实现端到端安全传输.

## 功能概述
- 安全文件传输 (单文件或整个目录)
- 短文本消息传输
- SSH 公钥传输 (wormhole ssh)
- 端到端加密 (基于 SPAKE2 密钥交换)
- 支持 Tor 中继传输 (txtorcon)

## OHOS 适配
- 纯 Python 项目, 使用 pip 安装, 无 ELF 二进制
- 不需要 ELF 签名, strip 或 RPATH 设置
- 需要大量 Python 依赖 (twisted, autobahn, cryptography 等)
- service_identity 版本需降级到 23.1.0 (兼容系统 cryptography 44.0.0)
- 使用 .pth 文件解决 pip 安装路径问题

## 排除与替代
无排除项, wormhole 和 magic-wormhole 命令均可正常使用

## 依赖
- Python 3.12+ (系统预装)
- twisted >= 17.5.0
- autobahn[twisted] >= 0.14.1
- spake2 == 0.9
- pynacl
- cryptography
- click
- tqdm
- humanize
- txtorcon >= 18.0.2
- zipstream-ng
- iterable-io
- qrcode >= 8.0
- service_identity (降级到 23.1.0)
- pyopenssl

## 功能验证
```bash
wormhole --version  # → magic-wormhole 0.24.0
wormhole send --help  # → 显示发送帮助
wormhole receive --help  # → 显示接收帮助
python3 -c "import wormhole; print(wormhole.__version__)"  # → 0.24.0
```

## 参考
- 官网: https://github.com/warner/magic-wormhole
- PyPI: https://pypi.org/project/magic-wormhole/