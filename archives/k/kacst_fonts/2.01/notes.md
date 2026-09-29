# kacst_fonts 2.01 适配记录

- **上游**：KACST（沙特阿卜杜勒阿齐兹国王科技城）阿拉伯字体集 2.01；平台任务名
  `kacst_fonts` / 版本 `2.01`。Debian 源包 `fonts-kacst` 的 `2.01+mry.orig` 引用
  同一份字体数据（`mry` 是 Debian 维护者的重打包标记，字体文件未改）。
  源文件名里的 `+` 在 URL 里写作 `%2B`。
- **交付**：`share/fonts/truetype/kacst/*.ttf`（14 套）+ `share/doc/kacst_fonts/{README,Copyright}`
  + `licenses/LICENSE`；`package_info()` 把 `share/` 前置进 `XDG_DATA_DIRS`，
  符合 freedesktop 字体查找约定。纯数据包，无编译步骤。
- **消费者用例**（rule12）：`test_package/consumer_fonts.py` 纯 Python 解析 TTF 真实表
  （`head`/`maxp`/`name`/`cmap` format 4/12），做码点覆盖统计与**字体选择**：
  阿拉伯文样本 8/8、阿拉伯标点 3/3，选中 `KacstArt`。
- **如实记录的消费结论**：这套字体是**阿拉伯专用**——14 套字体对拉丁字母与 ASCII 数字的
  覆盖率均为 0；文本栈必须为拉丁字符回退到其它家族。消费者用例把这一点作为**事实**记录
  并断言"全员不含"（若哪天被覆盖，说明字体集换了，用例会立刻报出来）。
- **本地验证**：`ohc-run.py conan-verify kacst_fonts 2.01` → PASS（消费者用例 + 自检 7/7）。
