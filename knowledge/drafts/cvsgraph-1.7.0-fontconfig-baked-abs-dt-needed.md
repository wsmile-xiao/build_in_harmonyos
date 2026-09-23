# cvsgraph 1.7.0 — ohpcd 发布包烤死绝对 DT_NEEDED：fontconfig/2.18.1 实证与规避

## 现象

- 真机 `conan create` + test_package **全绿**（渲染、运行时加载一切正常）
- CI 同一配方 test_package 阶段挂：

```
Error loading shared library /storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so:
(needed by /storage/Users/currentUser/.cache/conan2/p/fontc9e10589207d96/p/lib/libfontconfig.so.1)
ERROR: ... Error in test() method ... Error 127
```

注意失败库名是**不带 `.cache` 的完整绝对路径**，而 "needed by" 的库在
`.cache/conan2`——两台机器的缓存布局不同。

## 根因（ELF 解析实证）

ohpcd 已发布的 fontconfig/2.18.1 二进制包里，`libfontconfig.so.1.17.0`
对 libexpat 的 DT_NEEDED 是**绝对路径**：

```
fontconfig NEEDED: ['libfreetype.so.6',
 '/storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so',
 'libc.so']
```

- 构建机的 conan 缓存在 `$HOME/.conan2`，链接时把完整路径烤进了 NEEDED
- `conan2/p/<包哈希目录>` 跨机器**确定性同名**，于是在"恰好也有这个
  目录"的机器上（我们的真机主缓存）一切正常——**真机绿是侥幸命中**
- CI worker 缓存在 `$HOME/.cache/conan2` → 绝对路径不存在 → 加载失败
- 动态加载器对绝对 DT_NEEDED **不做搜索**，LD_LIBRARY_PATH 无效
- 同闭包的 libgd.so.3.0.11 对 libexpat 是裸 soname（正常），只有
  fontconfig 烤了绝对路径

## 修复（PR #10072 实证）

**规避（本包采用）**：换静态依赖变体——`gd/2.3.3`（static，
zlib+libpng；libpng16.so.16 解析实证仅 NEEDED libc.so）替代
`gd/2.3.3.1`（shared 含 fontconfig）。最终二进制运行期闭包只剩
libpng16.so.16 + libc，整类问题消灭。代价：TTF 字体不可用
（HAVE_GD_STRINGFT 不定义），cvsgraph 用 gd 内置位图字体（上游
`use_ttf=false` 本就是默认）。

**根治（另行立项）**：重编 fontconfig（修 soname/链接方式）后以 R37
后缀版本重发。勿把依赖包修复混进下游包 PR。

## 检测与判别

- 依赖闭包里所有 .so 跑 `readelf -d`（或 python struct 解析 .dynamic），
  DT_NEEDED 含 `/` 即烤死路径——**推送前查，别等 CI 揭盲盒**
- 判别口诀：loader 报错里**库名带完整路径且指向别机的 conan2/p** →
  烤死 DT_NEEDED；**库名裸 soname** → 才是 LD_LIBRARY_PATH 问题
- "真机绿 ≠ CI 绿"的典型样本：缓存布局差异使烤路径只在部分机器显形
