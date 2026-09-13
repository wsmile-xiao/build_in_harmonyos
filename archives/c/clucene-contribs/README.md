# clucene-contribs

CLucene 附加库（contributions）：德语/标准分析器、CJK 分析、highlighter
高亮、snowball 词干器等，与 clucene-core 同一上游源码树的
`src/contribs-lib/` 子树。

- 上游主页: https://clucene.sourceforge.net/
- 上游源码: SourceForge clucene 项目（clucene-core-2.3.3.4.tar.gz）；本包 conandata 使用字节级一致的权威镜像
  NetBSD pkgsrc distfiles CDN（CI worker 对 SourceForge 域不可达）
- 许可证: LGPL-2.0-or-later OR Apache-2.0
- 构建系统: CMake（旧式，最低声明 2.4.0）

## OHOS 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.3.3.4 | built | 上游测试 160/160 通过（含 contribs 套件） |

关键适配点见版本目录 `2.3.3.4/notes.md` 与 `manifest.yaml`。

## 依赖

- clucene-core/2.3.3.4（运行期 NEEDED libclucene-core.so.1；恒定 shared 变体）
- zlib/1.3.1.1（gzip 流；boost 为上游残余探测逻辑，实际无消费）
