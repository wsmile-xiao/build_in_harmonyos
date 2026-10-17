# libe-book

libe-book is a library and a set of tools for reading and converting
reflowable e-book formats — PalmDoc, TealDoc, Plucker, PeanutPress (eReader),
zTXT, RocketBook, TomeRaider, BroadBand eBook (BBeB), MS LIT, MS HTML Help,
FictionBook 2, and basic HTML/XHTML — into the librevenge document model.
It is part of the Document Liberation Project and is used by LibreOffice's
e-book import filters.

- Homepage: <https://sourceforge.net/p/libebook/>
- License: MPL-2.0
- Build system: autotools (dist tarball carries a pre-generated configure)

## OHOS 适配

| 版本 | 状态 | 说明 |
| --- | --- | --- |
| 0.1.4 | built | 纯库包（转换工具由 libe-book-tools 包跟踪）；liblangtag 语言标注关闭（可退化移植，见 0.1.4/manifest.yaml） |
