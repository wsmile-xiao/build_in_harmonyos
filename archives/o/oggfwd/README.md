# oggfwd

oggfwd 是一个极简的 Icecast 源客户端（命令行工具）：从标准输入读取 Ogg 流，
通过 libshout 转发到 Icecast 服务器，支持 `-m` 元数据文件（`SIGUSR1` 重新加载）、
`-n/-g/-d/-u` 流信息以及 `-T` TLS 模式。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.2-git20150412.506088e | published | Debian orig 快照（上游 git 506088e），HarmonyOS PC (aarch64) 适配 |

## 构建

```bash
conan create . --version=0.2-git20150412.506088e \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

产物：`bin/oggfwd`、`share/man/man1/oggfwd.1`

## 依赖

- libshout/2.4.6（传递依赖 libogg / libvorbis / speex / openssl，静态链接）

## 适配说明

见 [0.2-git20150412.506088e/notes.md](0.2-git20150412.506088e/notes.md)。
