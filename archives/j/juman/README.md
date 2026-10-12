# juman

日本語形態素解析システム（京都大学，BSD-3-Clause）：共有/静态库 `libjuman` + 辞書引きコマンド `juman` + 辞書構築ツール群。

- 上流項目：https://nlp.ist.i.kyoto-u.ac.jp/EN/index.php?JUMAN
- ソース：`https://deb.debian.org/debian/pool/main/j/juman/juman_7.0.orig.tar.bz2`
  （sha256 `c1df70ad34bd76c0d203c046af2884de87ed8bec74b63ef3075ae9335426e72c`，Debian 官方归檔）
- バージョン：`7.0`（2012 年リリース）

## 機能概述

- 日本語文の形態素解析（形態素、品詞、読み、活用形の出力）
- `libjuman` は、`juman`（コマンドライン）、`jserver`（サーバ）、`juman` クライアントの共通 C ライブラリ
- 辞書データ（`JUMAN.grammar` / `jumandic.*` / `autodic` / `wikipediadic`）を `share/juman` に同梱
- `juman` は mecab など他のツールチェーン（`mecab-jumandic`）の前段としても使われる

## OHOS 適合

ビルドシステムは autotools + libtool（tarball に 2011 年生成の `configure` が同棱されており、autoreconf 不要）。
2 つの可移植性パッチ（`patches/` 参照）：

1. **`config.sub` に aarch64 と ohos を追加**：tarball 同棱の `config.sub` は 2009-11-20 版で、`aarch64` も `ohos` も知らない。
   既存の `aalib/1.4p5` / `smpeg` と同じ三箇所を補うが、**2009 版は位置するアンカー行が 2001/2004 版と異なる**ため作業パッチの転用はできない。
2. **`configure` の `umask 077` → `022`**：HMDFS では新規ディレクトリに setgid が付くため、
   `umask 077` で作る config.status 作業ディレクトリ内のファイルが書き込めなくなる（E129/E011）。

さらに、レシピ側で次の 2 点を処理する：

- `generate()` で `-fcommon` を付与：`makeint.c` と `lib/grammar.c` が同じグローバル (`CurPath` / `JumanPath`) を
  tentative definition で定義しているため、clang のデフォルト（`-fno-common`）では重複シンボルになる（E491/E163）。
- `build()` で `PWD` を与える：HMDFS 上で libtool の `cd $dir && pwd` が実行パスを返せず相対パスの接頭辞が空になる（E114/E386）。

## 依存関係

- 第三者依存なし（標準 C ライブラリのみ）。辞書データはパッケージに同棱するため、実行時に外部データは不要。

## 機能検証

```bash
# バージョン確認
bin/juman -v            # → juman 7.0

# 実際の形態素解析（rc ファイルの辞書パスを絶対パスにしたものを渡す）
printf '日本語の形態素解析
' | bin/juman -r /path/to/jumanrc.absolute
# → 形態素列を出力し、最後に EOS
```

## 参考

- [公式ドキュメント](https://nlp.ist.i.kyoto-u.ac.jp/EN/index.php?JUMAN)
- [ソースリポジトリ](https://deb.debian.org/debian/pool/main/j/juman/)
