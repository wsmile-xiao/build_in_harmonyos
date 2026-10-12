# juman 7.0 適合筆記

## 編訳環境
- 構築システム: autotools + libtool（tarball 同棱の 2011 年生成 `configure`、autoreconf 不要）
- 編訳日付: 2026-10-11
- 編訳器: clang 15.0.4（`/data/service/hnp/bin/clang`）、clang++
- 状態: built

## バージョン説明
- 上流: https://nlp.ist.i.kyoto-u.ac.jp/EN/index.php?JUMAN （京都大学、BSD-3-Clause）、バージョン `7.0`
- ソース: `https://deb.debian.org/debian/pool/main/j/juman/juman_7.0.orig.tar.bz2`
  sha256 `c1df70ad34bd76c0d203c046af2884de87ed8bec74b63ef3075ae9335426e72c`
- バージョン番号は賽事クリアリストに沿用（初回適合、R37）

## 編訳手順
```bash
conan create archives/j/juman/7.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 問題と解決方法

| # | 問題 | 根因 | 解決方法 |
|---|------|------|----------|
| 1 | `configure` が `aarch64-linux-ohos` を認識せず `config.guess` が実行方法を推定できない | tarball 同棱の `config.sub` は 2009-11-20 版で `aarch64` / `ohos` 未対応（E007） | `--build/--host=aarch64-linux-ohos` を明示 + パッチ 0001（既存 `aalib/1.4p5` と同じ三箇所だがアンカー行が異なる） |
| 2 | `configure` が `./confXXXXXX/...: Permission denied` で停止 | `umask 077 && mktemp -d "./confXXXXXX"` で作る config.status 作業ディレクトリが HMDFS で使えない（E129/E011） | パッチ 0002：当該二箇所の `umask 077` → `022` |
| 3 | `makeint` のリンクで `duplicate symbol: CurPath` / `JumanPath` | `makeint/makeint.c` と `lib/grammar.c` が同名グローブルを tentative definition で定義。clang はデフォルト `-fno-common`（E491/E163） | `generate()` で `-fcommon` を付与（リポジトリ先例: `ant-phone/0.2.1` など） |
| 4 | libtool が相対パスの接頭辞を空で扱う | HMDFS 上で `cd $dir && pwd` がカレントディレクトリを返せない（E114/E386） | `build()` で `os.environ["PWD"] = self.build_folder` |
| 5 | 上流にテストスイートが無い | 2011 年生成の tarball で、`Makefile.in` に `check_PROGRAMS` / `TESTS` / `check` 目標が一切無い | `build()` 内で grep/find によるテストクリアリングを行い、ログ留証 + 5 件の消費者断言（`test_package/test_juman.c`） |

## ソース修正
- `patches/0001-config-sub-aarch64-ohos.patch` — config.sub に `aarch64` と `ohos` を追加（三箇所）
- `patches/0002-configure-config-status-umask.patch` — configure 内の `umask 077` を `022` に（二箇所）

## 依存バージョン
- 第三者依存なし

## 検証結果
```bash
conan create archives/j/juman/7.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0。交付: lib/libjuman.a、include/juman.h、include/juman_pat.h、bin/juman、
# libexec/juman/{makeint,makemat,makepat,dicsort}、share/juman/**、etc/jumanrc、licenses/COPYING

# 消費者用例（juman::juman にリンクして公開 C API を験す）
CHECK-OK: my_strlen() counts the characters of a string
CHECK-OK: my_strcpy()+my_strcmp() round-trip
CHECK-OK: my_strcmp() distinguishes different strings
CHECK-OK: lower() folds an upper case letter
CHECK-OK: upper() folds a lower case letter
JUMAN_CONSUMER_CHECKS=5 FAILURES=0
JUMAN_CONSUMER_OK

# コマンド実行確認
bin/juman -v                                   # → juman 7.0
printf '日本語の形態素解析' | bin/juman -r <rc absolute paths>
# → 形態素列を出力し EOS で終了
```

上流テスト: juman 7.0 は **テストスイートを同棱しない**（無 `tests/` 目録、
Makefile に `check` 目標 / `TESTS` / `check_PROGRAMS` 無し）。そのため TEST_QUALITY_SPEC に従い
`build()` 内にクリアリング命令を埋め込み、消費者用例で公開 API の契約をカバーする。

## 注意事項
- 同棱の `etc/jumanrc` の辞書パスは `//share/juman/...`（コンパイル時の prefix 相对）で記述されている。
  パッケージを prefix 以外に展開して `bin/juman` を使う場合は、`-r` で辞書パスを絶对パスにした rc ファイルを渡す（`JUMANRC` 環境変数ではなく `-r` オプション）。
- 辞書データ（`share/juman`）が約 32 MB あり、パッケージ体が大きい。
