/* 消费者验证：真实调用 ClassAds 库 API 并断言行为。
 * 1) 解析 ClassAd 文本并读取整型属性；
 * 2) 构造 Job/Machine 两个 ClassAd 并验证 symmetricMatch；
 * 3) PrettyPrint 输出解析结果。 */
#ifndef _LIBCPP_DISABLE_EXTERN_TEMPLATE
#define _LIBCPP_DISABLE_EXTERN_TEMPLATE
#endif
#include "classad/classad_distribution.h"
#include <iostream>
#include <string>

using namespace std;
#ifdef WANT_CLASSAD_NAMESPACE
using namespace classad;
#endif

int main()
{
    ClassAdParser parser;
    ClassAd *ad = parser.ParseClassAd("[memory = 4096; type = \"job\"]");
    if (ad == NULL)
    {
        cerr << "ParseClassAd failed" << endl;
        return 1;
    }
    int memory = 0;
    if (!ad->EvaluateAttrInt("memory", memory) || memory != 4096)
    {
        cerr << "EvaluateAttrInt(memory) != 4096" << endl;
        return 1;
    }

    string job_text = "[Requirements = (other.Type == \"Machine\" && other.memory >= 4000); Type = \"Job\"; Memoryused = 6000;]";
    string machine_text = "[Requirements = (other.Type == \"job\" && other.memoryused < 8000); Type = \"machine\"; Memory = 5000;]";
    ClassAd *job_ad = parser.ParseClassAd(job_text);
    ClassAd *machine_ad = parser.ParseClassAd(machine_text);
    if (job_ad == NULL || machine_ad == NULL)
    {
        cerr << "ParseClassAd(job/machine) failed" << endl;
        return 1;
    }
    MatchClassAd match_ad(job_ad, machine_ad);
    bool can_evaluate = false, ads_match = false;
    can_evaluate = match_ad.EvaluateAttrBool("symmetricMatch", ads_match);
    if (!can_evaluate || !ads_match)
    {
        cerr << "ClassAd symmetricMatch failed" << endl;
        return 1;
    }

    PrettyPrint printer;
    string printed;
    printer.Unparse(printed, ad);
    cout << "classads consumer test passed; parsed: " << printed << endl;
    // 与上游 sample.cpp 一致：ClassAd 由解析器内部结构持有，进程退出回收；
    // 显式 delete 与 MatchClassAd 的内部引用交织时行为未定义。
    return 0;
}
