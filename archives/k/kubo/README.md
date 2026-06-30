# kubo

Kubo 是 IPFS（星际文件系统）的 Go 语言实现，提供去中心化的文件存储和共享。

## 描述
Kubo（原名 go-ipfs）是 IPFS 协议的参考实现。它提供 P2P 文件系统、内容寻址存储、去中心化数据共享等功能，支持 IPFS 节点管理和数据操作。

## 已编译版本
- 0.42.0 (2026-06-17)

## 依赖
- Go 1.26.3

## 特性
- IPFS 节点初始化和管理
- 内容寻址文件存储
- P2P 数据共享
- DAG 数据结构操作
- MFS（Mutable File System）支持
- HTTP Gateway

## 补丁
- 0001-go.mod.patch: 降级 Go 版本声明以适配本地 Go 工具链

## 使用方法
```bash
# 初始化 IPFS 节点
ipfs init

# 启动节点
ipfs daemon

# 添加文件
ipfs add myfile.txt

# 获取文件
ipfs cat <hash>
```

## 注意事项
- CGO_ENABLED=0 编译，纯静态二进制
