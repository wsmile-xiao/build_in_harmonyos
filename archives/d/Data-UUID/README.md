# Data-UUID

Perl UUID 生成模块，提供 UUID v1 和 v3 的生成、转换和比较功能。

## 功能

- **UUID v1 生成**：基于时间戳和节点 ID
- **UUID v3 生成**：基于命名空间和名称（MD5）
- **字符串转换**：`to_string()`, `from_string()`
- **格式转换**：`create_hex()`, `create_b64()`
- **UUID 比较**：`compare()`

## OpenHarmony 适配

### 版本 1.227

- **链接方案**：使用 `-nostartfiles -nodefaultlibs + musl libc.so` 避免 CRT 文件缺失
- **SELinux**：需安装到 `/data/service/hnp` 系统目录获得正确的标签
- **依赖**：musl 1.2.5 (提供 libc.so)

### 安装

通过 cmd-pkgs 公共安装脚本：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- Data-UUID 1.227
```

## 参考

- [CPAN Data::UUID](https://metacpan.org/pod/Data::UUID)
- [RFC 4122 - UUID 规范](https://tools.ietf.org/html/rfc4122)