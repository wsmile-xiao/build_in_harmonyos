# DRAFT-zita-lrx-0.1.2-upstream-url-domain-misdirection

## 现象（zita-lrx 0.1.2 实录）

任务派发时上游情报为「kokkinizita.net/linuxaudio/downloads/ 直探 404（多文件名变体全 404）」，
表面上像"官方源不可达/版本不存在"。

## 定位过程（三角交叉）

1. **同族先例 conandata**：`git show origin/main:archives/l/libzita-resampler/1.11.2/conandata.yml`
   显示同作者（Fons Adriaensen）同站先例用的域名是 **kokkinizita.linuxaudio.org**（.org，非 .net），
   目录同为 `/linuxaudio/downloads/`。
2. **Debian watch 权威旁证**：`https://sources.debian.org/data/main/z/zita-lrx/0.1.2-1/debian/watch`
   内容为 `http://kokkinizita.linuxaudio.org/linuxaudio/downloads/index.html` +
   文件名模式 `zita-lrx-(.*)\.tar\.bz2`（Debian bullseye→sid 全 suite 跟踪 0.1.2-1）。
3. **HEAD 实测**：`https://kokkinizita.linuxaudio.org/linuxaudio/downloads/zita-lrx-0.1.2.tar.bz2`
   → HTTP 200，Content-Length 21838，Content-Type application/x-bzip2，
   Last-Modified 2018-08-25（与 0.1.2 发布年代吻合）。sha256 实测
   `54740dc563ffb3f0a26aabd20dc6905f42a4e77dfb80ae71c3a2899eb8418c97`。

三证一致 → 官方 URL 实锤写入 conandata.yml（R39 单条官方源）。

## 根因

个人/小团队上游站点的域名变体（.net/.org/.com）极易混淆；派发情报引用了错误变体导致
整批文件名轮询 404。这不是"版本不存在"，是"探错了域"。

## 方案（可复用三步法）

```
上游直探 404
  ├─ ① 同仓同作者/同站先例包 conandata.yml → 拿到正确域名与目录形态
  ├─ ② Debian sources 的 debian/watch → 拿到官方版本页与文件名模式
  └─ ③ HEAD 请求候选 URL → 200 + Content-Type + Last-Modified 年代吻合 = 实锤
三证一致 → 写 conandata
不一致/仍 404 → 用 Debian orig tarball + 正文如实申报来源；双 404 → 存证报批不硬做
```

## 边界与豁免

- 该技法适用于"上游存在但域名/路径不明确"的场景；不适用于上游真消失（此时走 Debian
  orig tarball 申报线）。
- sha256 必须从最终采用的 URL 实测，不从第三方转抄。

## 关联

- similar_to E155：同为"上游源 404"场景族，但 E155 是 CPAN backpan 替代（Perl 生态），
  本条是域名错位三角定位（通用 C/C++ 小件生态），根因与手段均不同，查重为零命中。
