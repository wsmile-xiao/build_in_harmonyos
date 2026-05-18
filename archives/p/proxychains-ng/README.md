# proxychains-ng

## 简介
proxychains-ng 是一个强制任意 TCP 连接通过代理的工具（proxychains new generation）。

## 功能
- 让任何程序通过 SOCKS4、SOCKS5、HTTP 代理连接
- 通过 LD_PRELOAD 动态库劫持 connect() 系统调用
- 支持代理链（proxy chaining）
- 支持动态 DNS 解析

## 使用方式
```bash
proxychains4 <command>
proxychains4 -f /path/to/config.conf <command>
proxychains4 -q <command>  # quiet mode
```

## 配置文件
默认配置文件：`$PREFIX/etc/proxychains.conf`

配置示例：
```
strict_chain
proxy_dns 
[ProxyList]
socks5 127.0.0.1 1080
```

## 编译版本
- 4.16 (2026-05-14)

## 依赖
- 无特殊依赖，仅需标准 C 库
- 需要动态链接功能（LD_PRELOAD）

## 注意事项
- 需要配置文件才能正常运行
- 适用于需要通过代理访问网络的场景
