# quicklisp

Quicklisp —— Common Lisp 的库管理器。本归档收录的是它的**引导（bootstrap / quickstart）
文件** `quicklisp.lisp`。

| 项 | 值 |
|---|---|
| 上游 | https://github.com/quicklisp/quicklisp-bootstrap |
| 官网 | https://www.quicklisp.org |
| 许可 | MIT（Expat） |
| 当前版本 | 20150128（上游版本串 `2015-01-28`） |
| 构建系统 | 无（纯数据/脚本重分发，无 C/C++ 源码、无编译产物） |

## 为什么没有编译步骤

上游 `Makefile` 只有 `all:`（空目标）与 `tag:`（发版打 tag），源码包只含
`LICENSE.txt` / `Makefile` / `README.txt` / `quicklisp.lisp`，Debian 源码包标注
`Architecture: all`。因此本归档按「无构建/打包族」适配：把启动文件安装到包内
`share/quicklisp/`，并用 `runenv/buildenv` 暴露 `QUICKLISP_BOOTSTRAP`。

## 使用（OHOS）

```sh
# 激活 Conan runenv 后（提供 QUICKLISP_BOOTSTRAP）
. "<pkg>/share/quicklisp/quicklisp-ohos-env.sh"
# 然后在 Common Lisp 实现中：
#   (load (uiop:getenv "QUICKLISP_BOOTSTRAP"))
#   (quicklisp-quickstart:install :path (uiop:getenv "QUICKLISP_HOME"))
```

运行期需要一个 Common Lisp 实现（本仓制品仓提供 `ecl/24.5.10`，OHOS/armv8）。
`quicklisp-ohos-env.sh` 在 HOME 缺失（OHOS 沙箱）时把 `QUICKLISP_HOME` 回退到
`/storage/Users/currentUser/quicklisp`。

## 版本索引

| 版本 | 状态 |
|---|---|
| 20150128 | built |

详见 `20150128/notes.md`。
