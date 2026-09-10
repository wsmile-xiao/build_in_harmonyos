# DRAFT-6051-libnxml-0.18.5-remote-automake-pkg-missing-dotfiles — 远程 automake/1.18 二进制包 bin 目录丢失点文件（.aclocal-real/.automake-real），本地 --build 重建规避

- 触发事件：libnxml 0.18.5 适配，conan create 首次解析 tool_requires automake/1.18
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6051

## 现象

conan create 从远端（ohpcd）下载 automake/1.18 预编译二进制包后，
`bin/aclocal`（sh 包装器）存在但 `exec $here/.aclocal-real` 失败：
`.aclocal-real` 文件不存在。同时包目录留下 `b.dirty` / `p.dirty` 痕迹。
错误形态：

```
Can't exec "/…/p/bin/.aclocal-real": No such file or directory at …/bin/aclocal line N.
```

## 根因

automake/1.18 conan 包的 package() 会把 `aclocal` 改名为 `aclocal-real`
（点文件）并生成 sh 包装器。远端二进制包在打包或传输环节丢失了这些
点文件（dotfile），且 conan 对下载包不做完整性校验（conanmanifest 只对
文件列表做 sha 校验，缺文件未必致命）→ 半残包仍被当作有效缓存命中。

另一个次生坑：多次 create 会在 `.conan2/p/b/` 留下多个失败的 automake
构建目录（autom15ba…、automac06b…），其中部分带 `p.dirty`，conan list
显示包存在但 `p/` 目录缺失，解析时行为混乱。

## 可复用处置

1. 症状速查：
   ```bash
   ls <automake pkg>/p/bin/.aclocal-real   # 不存在即中招
   ```
2. 清掉远端包并强制本地构建（一次即可）：
   ```bash
   conan remove "automake/1.18" -c
   conan install --requires automake/1.18 --build="automake/*" \
     -pr:h=~/.conan2/profiles/ohos-aarch64-local \
     -pr:b=~/.conan2/profiles/ohos-aarch64-local
   # 验证：
   ls ~/.conan2/p/b/autom*/p/bin/.aclocal-real
   ```
3. 若 `.conan2/p/b/` 有残留 automac*/autom15* 半成品目录，`conan remove`
   清理后重建，避免脏目录干扰。

## 判定要点

- 与 DRAFT-6049（perl 双 arch 冲突）区分：本条是**文件缺失**（No such
  file or directory），6049 是**XS 模块失配**（Cwd.c handshake mismatch）；
  前者修包，后者修解释器环境，别混。
- 本地重建后若仍失败，先看是不是 6049 的 perl 问题叠加。

## 实证

- libnxml-0.18.5 适配：远端包 autom3efa…（bin 无 .aclocal-real）→
  conan remove + --build 重建 autom2418…（bin 完整）→ autoreconf 链恢复；
- 重建后正常完成 conan create 全链（CREATE=0）。
