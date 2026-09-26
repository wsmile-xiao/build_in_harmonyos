#!/usr/bin/env python3
"""Conan test_package — xset/1.2.5（消费者冒烟测试）

xset 是 X 客户端命令行工具，没有可链接的公开 API ⇒ 消费者测试**真实执行打包
二进制**（R34）。六条硬断言都不需要 X server，每条绑定 xset.c 的一个**在该环境
下确实可达**的代码出口：

  1. `xset -version` 在 XOpenDisplay 之前 `puts(PACKAGE_STRING); exit(0)`
     （xset.c:171-173）⇒ 断言 rc=0 且输出**恰为** `xset 1.2.5`（版本串未被归一化）。
  2. `xset`（无任何选项）在参数扫描后走 `usage(NULL)`（xset.c:178-180）⇒
     断言 rc=0 且 stderr 命中 usage 行。注意 **rc=0 是上游事实**：`usage()` 尾部
     是 `exit(EXIT_SUCCESS)`（xset.c:1648），不是本包 bug，故不拿"非 0 退出"当判据。
  3. usage 文本里的 DPMS 小节包在 `#ifdef DPMSExtension` 内（xset.c:1593-1604）
     ⇒ 断言该小节存在，**正向反证 libxext 依赖真的生效**（xext 探测失败时
     DPMSExtension 不成立，整段会被编译掉）。
  4. `xset -display <不存在的显示名> q` ⇒ 断言 rc!=0 且 stderr 为
     `unable to open display`（xset.c:182-187）。这条同时验证二进制**能被动态
     装载**（libX11.so.6 / libXext.so.6 的 DT_NEEDED 全部解析成功）且真的走到
     Xlib 连接路径。
  5. `xset -display` 与 `xset -d`（缺值）⇒ 断言两者都命中
     `missing argument to -display` 并接 usage 文本、rc=0（xset.c:167-170 →
     usage(fmt)，xset.c:1569-1576 + 1648）。**可达性依据**：这条错误发生在
     main() 的**第一轮扫参循环**（xset.c:165-177）里，位置在 182 行
     `XOpenDisplay` **之前**，因此无 X server 也能触发。
  6. usage 文本**不含** `To control font cache` ⇒ **反向反证**配方的
     `--without-fontcache` 真实传到 configure（该小节在 `#ifdef FONTCACHE` 内，
     xset.c:1605-1612）。与第 3 条一正一反，共同排除"整段 usage 文本被整体
     裁掉/整体编进"这两种假绿。

★ 本轮（第三棒）改掉了一条**不可达**的断言：原先第 5 条断言
  `xset -no-such-option` 命中 xset.c:756 的 `usage("unknown option %s", arg)`，
  实测失败。原因是 xset.c:165-177 的第一轮扫参对**任意未识别参数**只置
  `hasargs = True`（174-176 行），随后 182 行无条件 `XOpenDisplay`；而 756 行
  所在的是 189 行起的**第二轮**解释循环，**必须先有可用的 X 连接**。故无 X
  server 时 `xset -no-such-option` 的真实出口是 `unable to open display ""`
  （rc=1），`unknown option` 分支根本不可达。⇒ 换成上面第 5 条真正可达的
  参数解析错误分支。这是**断言写错了**，不是本包缺陷。

未覆盖功能面（如实声明，见 test_package/MANIFEST.yml 与 notes.md）：需要真实
X server 的功能路径（`xset q` 查询、b/c led/mouse/kbd、fp 字体路径、dpms force、
s 屏保、r 路由）在本环境无法断言；xset.c:756 的 unknown option 分支与
xset.c:1681/1684 的 XmuPrintDefaultErrorMessage 调用点同样需要 X 连接，本次未
断言（libXmuu 已静态链入由 readelf 符号表另证，见 notes.md）。
"""

import os

from conan import ConanFile


class XsetTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 执行 ELF 不可靠，用 bash 包装（同 xsel/1.2.1）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_xset.sh", env="conanrun")
