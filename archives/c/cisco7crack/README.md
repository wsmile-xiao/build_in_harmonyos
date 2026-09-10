# cisco7crack

`cisco7crack` 用于加解密 Cisco IOS 的 type-7（enable）口令。type-7 是 Cisco 的
弱混淆方案：首两字节为 0..15 的随机偏移，其余为口令字节与固定字符块
`dsfd;kfoA,.iyewrkldJKDHSUB` 异或后的 ASCII-hex 表示，本工具可解密还原，
也可按指定偏移（`-c#<0..15>`）加密生成。

```
$ cisco7crack -d 104D000A0618
Plain string     : cisco
```

- 上游仓库：https://github.com/madrisan/cisco7crack
- 版本：git 快照 f1c21dd（2012-12-21，first commit），版本号 0.0-git20121221.f1c21dd
- 许可证：GPL-2.0-or-later（源码头注释声明）
- 构建系统：无（单文件 C 程序，配方直接编译）
- 类型：命令行工具（无库产物）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.0-git20121221.f1c21dd | built | 首次适配 HarmonyOS PC (aarch64) |
