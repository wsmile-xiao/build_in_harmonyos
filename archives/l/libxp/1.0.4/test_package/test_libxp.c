/* libxp/1.0.4 consumer link + behaviour test.
 *
 * libXp 里唯一一族不需要 X server 的公开接口就是 locale 提示机制
 * （XpSetLocaleHinter / XpGetLocaleHinter / XpGetLocaleNetString），
 * 本测试全部走它，因此可以在无图形服务的 OHOS CI worker 上真实执行。
 * 断言的都是可观察行为：返回的字符串内容、%locale% 关键字的替换结果，
 * 以及「被 C 库拒绝的 locale 不得被当成生效值上报」。
 *
 * 库自身与 libX11 / libXext / libXau 的符号也都经由链接被真实解析
 * （libXp 用 -no-undefined 构建，XpExtUtil.c 调 Xext*、XpLocale.c 调 Xau*）。
 */

#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <X11/extensions/Print.h>

static int checks = 0;
static int failures = 0;

static void check(int ok, const char *msg)
{
    checks++;
    if (!ok) {
        failures++;
        fprintf(stderr, "FAIL: %s\n", msg);
    }
}

#define HINTER_DESC "XOPEN;%locale%;01_00;XFN-001001"

/* hinter 契约（XpLocale.c:242/251）：回调返回的字符串由 **libXp 自己**
 * 用 XFree() 释放，所以这里必须返回堆内存。
 *
 * 用 malloc() 而不是 libXp 源码里那个 Xmalloc()：Xmalloc 声明在 libX11 的
 * **私有头** <X11/Xlibint.h> 里，是 libX11 导出的符号，消费者的头文件集
 * 里既没有它、链接行上也只有 -lXp（lld 不会顺着 libXp.so 的 DT_NEEDED
 * 去 libX11 里找符号，实测 `ld.lld: error: undefined symbol: Xmalloc`）。
 * XFree 最终就是 free()，malloc 分配的内存交给它释放是配对的。 */
static char *custom_hinter(void)
{
    char *out = (char *) malloc(sizeof("de_DE"));
    if (out != NULL) {
        strcpy(out, "de_DE");
    }
    return out;
}

int main(void)
{
    XPHinterProc proc = NULL;
    char *desc;
    char *net;

    /* ── 场景一：默认 hinter —— net string 就是进程当前生效的 LC_CTYPE ── */
    setlocale(LC_CTYPE, "C");
    XpSetLocaleHinter(NULL, NULL);

    desc = XpGetLocaleHinter(&proc);
    check(proc != NULL, "默认 hinter 必须安装一个非空回调");
    check(desc == NULL, "默认 hinter 的描述是 NULL");
    if (desc != NULL) {
        XFree(desc);
    }

    net = XpGetLocaleNetString();
    check(net != NULL, "默认 hinter 下 net string 不得为 NULL");
    if (net != NULL) {
        check(strcmp(net, setlocale(LC_CTYPE, NULL)) == 0,
              "默认 hinter 下 net string 必须等于实际生效的 LC_CTYPE locale");
        XFree(net);
    }

    /* ── 场景二：%locale% 关键字必须被 hinter 返回值替换 ── */
    XpSetLocaleHinter(custom_hinter, HINTER_DESC);

    desc = XpGetLocaleHinter(&proc);
    check(proc == custom_hinter, "XpGetLocaleHinter 应回传已安装的回调");
    check(desc != NULL && strcmp(desc, HINTER_DESC) == 0,
          "XpGetLocaleHinter 应回传已安装的描述");
    if (desc != NULL) {
        XFree(desc);
    }

    net = XpGetLocaleNetString();
    check(net != NULL, "自定义 hinter 下 net string 不得为 NULL");
    if (net != NULL) {
        check(strcmp(net, "XOPEN;de_DE;01_00;XFN-001001") == 0,
              "%locale% 必须被 hinter 的返回值替换");
        check(strstr(net, "%locale%") == NULL,
              "结果里不得残留未替换的 %locale% 关键字");
        XFree(net);
    }

    /* ── 场景三：描述里没有 %locale% 时以描述为准（hint 被丢弃） ── */
    XpSetLocaleHinter(custom_hinter, "NO_KEYWORD");

    net = XpGetLocaleNetString();
    check(net != NULL && strcmp(net, "NO_KEYWORD") == 0,
          "描述不含 %locale% 时应原样返回描述");
    if (net != NULL) {
        XFree(net);
    }

    /* ── 场景四（鸿蒙特有）：musl 拒绝的 locale 不得被当成生效值上报 ──
     *
     * OHOS 用 musl，镜像里没有 locale 数据目录，setlocale() 对
     * "C"/"POSIX" 以外的请求一律返回 NULL 并保持原 locale 不变。
     * locale 提示机制必须如实上报**实际生效**的 locale：既不能因为
     * hint 解析失败而返回 NULL/崩溃，也不能把调用方请求、但被 C 库
     * 拒绝的名字当作生效值返回（那会让 XpGetPrinterList 之类的请求
     * 带上一个根本不存在的 locale_hint）。
     * glibc 上同一段代码走 else 分支，断言的是「跟随生效 locale」，
     * 两条分支都在断言同一个不变量。
     */
    setlocale(LC_CTYPE, "C");
    XpSetLocaleHinter(NULL, NULL);
    {
        const char *requested = "en_US.UTF-8";
        const char *accepted = setlocale(LC_CTYPE, requested);
        const char *effective = setlocale(LC_CTYPE, NULL);

        net = XpGetLocaleNetString();
        check(net != NULL,
              "hint 非空时即使 C 库拒绝切换 locale 也必须返回可用的 net string");
        check(net != NULL && effective != NULL && strcmp(net, effective) == 0,
              "net string 必须等于 C 库实际生效的 locale");
        check((accepted != NULL) == (net != NULL && strcmp(net, requested) == 0),
              "OHOS/musl：被 C 库拒绝的 locale 不得被当成生效值上报；被接受时须跟随");
        if (net != NULL) {
            XFree(net);
        }
    }

    printf("libxp consumer checks: %d/%d passed\n", checks - failures, checks);
    return failures == 0 ? 0 : 1;
}
