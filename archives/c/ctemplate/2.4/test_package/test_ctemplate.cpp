#include <cstdio>
#include <string>
#include <ctemplate/template.h>
#include <ctemplate/template_dictionary.h>

int main() {
    /* 鸿蒙特有验证：消费打包后的头+静态库，从字符串展开模板。
       断言展开结果逐字节相等（含 modifier 转义路径）。
       注意：ExpandTemplate 首参是模板【文件名】——字符串模板必须走
       Template::StringToTemplate（CI #44147 实测误用报
       "Unable to locate file {{NAME}} ..."）。 */
    ctemplate::TemplateDictionary dict("test");
    dict.SetValue("NAME", "HarmonyOS<PC>");
    dict.SetValue("ESC", "<b>&\"</b>");

    ctemplate::Template* tpl = ctemplate::Template::StringToTemplate(
        "{{NAME}} {{ESC:h}} {{ESC:j}}", ctemplate::DO_NOT_STRIP);
    std::string out;
    bool ok = tpl != NULL;
    if (ok)
        tpl->Expand(&out, &dict);
    const char* want = "HarmonyOS<PC> &lt;b&gt;&amp;&quot;&lt;/b&gt; \\x3cb\\x3e\\x26\\x22\\x3c/b\\x3e";
    printf("expanded: %s\n", out.c_str());
    if (!ok || out != want) {
        printf("FAIL: mismatch, want: %s\n", want);
        return 1;
    }
    printf("PASS: ctemplate expand + modifiers correct on HarmonyOS\n");
    return 0;
}
