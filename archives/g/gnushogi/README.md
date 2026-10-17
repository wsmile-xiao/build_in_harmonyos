# gnushogi

GNU Shogi — 日本将棋（shogi）引擎。提供文本界面的对弈引擎二进制 `gnushogi`，
支持人机对弈、开局书编译（bbk）与置换表。上游：https://www.gnu.org/software/gnushogi/

适配说明：OHOS 上以 clang 交叉/本机构建（-fcommon，--without-curses 文本 UI），
二进制经 binary-sign-tool 自签后可直接执行。
