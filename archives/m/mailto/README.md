# mailto

[WWW 邮件网关](https://www.apache.org/distware/mailto/)（Andreas Ley，1994–1998，Apache 软件基金会发布）——
把 HTTP 表单提交解析成 MIME 邮件，并交给本机 MTA（`sendmail`）投递的 CGI 程序。

## 它做什么

给定一个浏览器提交的表单（`QUERY_STRING` 或 `POST` 正文），`mailto` 会：

1. 解析各字段；`NAME="To"` / `NAME="Subject"` / `NAME="Acknowledge"` 有特殊含义
2. 把字段拼装成 MIME 邮件：一行内容写成 `"<name>: <content><LF>"`，
   多行内容写成 `"<name>:<LF>…<LF>.<LF>"`（行首句点前再加一个句点）
3. 通过 `sendmail` 投递
4. 可选：按 `mailto.conf` 访问控制文件决定谁被允许通过网关发信
   （1999 年的设计背景是"WWW 上匿名发信不可取"）

## 用法

```
mailto [-h] [-v]
```

| 选项 | 作用 |
|---|---|
| `-h` | 打印用法 |
| `-v` | 打印版本横幅 |
| `-D <domain>` | 为发信人补全 `@domain` 后缀 |

正常运行时不接受位置参数，从环境变量读取 CGI 变量
（`QUERY_STRING` / `CONTENT_LENGTH` / `REQUEST_METHOD` / `REMOTE_USER` …）。

## 快速验证

`mailto` 不设任何 CGI 环境变量直接运行，会输出默认的 CGI 表单页：

```
$ mailto
Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<!-- mailto v1.3.2 (c) 1994-1998 by Andreas Ley -->
<HTML>
<HEAD>
<TITLE>WWW Mail Gateway</TITLE>
...
```

这就是本包消费者测试的断言依据 —— 零网络、零 MTA。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.3.2 | `mailto/1.3.2` | 已适配（aarch64） |

## 授权

Apache-2.0（见配方 `licenses/` 与 tarball 内 `COPYING`）。
