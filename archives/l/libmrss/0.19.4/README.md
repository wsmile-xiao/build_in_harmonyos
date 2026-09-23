# libmrss 0.19.4（HarmonyOS 三方库存档）

mRss — C 语言 RSS/Atom feed 解析、写出与创建库（作者 baku / Andrea
Marchesini）。上游：https://github.com/bakulf/libmrss

## 归档内容

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（NEWS 规避 + autoreconf 自举（pkg.m4/libtool.m4 注入）+ E007 + 链接期 RUNPATH 规避 + 上游测试 + 示例验证） |
| conandata.yml | 官方 tarball URL 与 SHA256（0 补丁） |
| manifest.yaml | 构建元数据 |
| test_package/ | 消费者测试 1/1（内联 RSS fixture：创建/解析/字段/保存/非法 XML） |
| tests/ohos-libmrss-consumer/ | 鸿蒙特有测试 1/1（ELF64/codesign/SONAME/NEEDED/宿主路径/OHOS 实跑） |

## 快速使用

```bash
conan create . --build=missing   # 配合本仓库 ohos profile
```

## 关键结论

- 依赖链：libmrss → libnxml/0.18.5（PKG_CHECK_MODULES 强制）→
  curl/8.15.0；三者均为库依赖；自举另需 pkgconf/3.0.5（pkg.m4）
- tarball 缺 NEWS 实体文件，automake 报 required file './NEWS' not
  found；自举前 touch NEWS 规避（DRAFT-6053，0 源码补丁）
- 上游 1 项正式测试（test/new，纯离线）真实运行通过；noinst 示例
  parser/write/time/search 单独构建运行验证（URL 数据源走本地
  127.0.0.1 HTTP，feed 由配方内联生成）
- SONAME：version-info 19:4:19 → libmrss.so.0（产物
  libmrss.so.0.19.4 与推导一致）
- 产物无 DT_RUNPATH（鸿蒙包规范）：OHOS lld 嵌入 .codesign 段且
  musl 加载器校验，链接后改字节即失效——规避全部在链接期完成
  （libnxml 复制到构建树内无 .la 目录再 -L/-l，绕开 libtool 对
  .la 依赖的 libdir 硬编码）
- 本机即 OHOS aarch64，原生构建，不用 --build/--host
