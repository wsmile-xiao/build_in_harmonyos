# libnxml 0.18.5（HarmonyOS 三方库存档）

nXml — 小型 C XML 解析/写出库（作者 baku / Andrea Marchesini）。
上游：https://github.com/bakulf/libnxml

## 归档内容

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools 自举 + E007 + 上游测试 + 示例验证） |
| conandata.yml | 官方 tarball URL 与 SHA256（0 补丁） |
| manifest.yaml | 构建元数据 |
| notes.md | 适配笔记（问题/根因/解决方案全记录） |
| test_package/ | 消费者测试 1/1（Conan 安装后真实调用公开 API） |
| tests/ohos-libnxml-consumer/ | 鸿蒙特有测试 1/1（ELF64/codesign/SONAME/NEEDED/宿主路径/OHOS 实跑） |

## 快速使用

```bash
conan create . --build=missing   # 配合本仓库 ohos profile
```

## 关键结论

- curl 是库依赖（NEEDED libcurl.so），非构建依赖、非仅测试命令
- 上游 3 项正式测试（new/easy/test_base）全部真实运行通过；easy 的
  上游域名被注册局下线，以本地 HTTP 等价数据源替代
- 本机即 OHOS aarch64，原生构建，不用 --build/--host
