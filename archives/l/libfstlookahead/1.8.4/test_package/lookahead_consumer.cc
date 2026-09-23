// libfstlookahead 1.8.4 消费者验证（鸿蒙侧新增用例）
//
// 目的：在真机上用**包内已安装**的头文件与库，真实调用 LookAheadFst 扩展的 API，
// 而不是只检查文件存在。覆盖三层：
//   1) 注册面：三个 LookAheadFst 类型名在 FstRegister 中可解析 —— 注册器静态对象位于
//      libfstlookahead.a（arc/ilabel/olabel_lookahead-fst.cc），链接时若被剔除即为 nullptr；
//   2) 运行时行为：构造 StdArcLookAheadFst、状态/弧/终态与 MatcherFst 的匹配器语义；
//   3) 端到端：写出 FST 再用 Fst<StdArc>::Read 读回 —— 该路径经
//      FstRegister::GetReader(<type>) 分派回扩展库的 reader（fst.h:266），验证扩展真正可用。
//
// 退出码 0 = 全部断言通过；非 0 = 有断言失败。末行输出机器可读计数。

#include <cstdio>
#include <memory>
#include <string>

#include <fst/arc.h>
#include <fst/const-fst.h>
#include <fst/expanded-fst.h>
#include <fst/fst.h>
#include <fst/lookahead-matcher.h>
#include <fst/matcher-fst.h>
#include <fst/matcher.h>
#include <fst/register.h>
#include <fst/vector-fst.h>

namespace {

int g_total = 0;
int g_failed = 0;

void Check(bool ok, const char *what) {
  ++g_total;
  if (ok) {
    std::printf("ok   %s\n", what);
  } else {
    ++g_failed;
    std::printf("FAIL %s\n", what);
  }
}

}  // namespace

int main(int argc, char **argv) {
  using Arc = fst::StdArc;
  const std::string path = argc > 1 ? argv[1] : "lookahead_consumer.fst";

  // 1) 扩展库注册面。
  Check(fst::FstRegister<Arc>::GetRegister()->GetEntry("arc_lookahead").reader != nullptr,
        "register: arc_lookahead reader present");
  Check(fst::FstRegister<Arc>::GetRegister()->GetEntry("ilabel_lookahead").reader != nullptr,
        "register: ilabel_lookahead reader present");
  Check(fst::FstRegister<Arc>::GetRegister()->GetEntry("olabel_lookahead").reader != nullptr,
        "register: olabel_lookahead reader present");

  // 2) 构造一个 3 状态线性 FST：0 -1/1/0.5-> 1 -2/2/0.25-> 2(终态)，另加 0 -3/3/1.5-> 2。
  fst::VectorFst<Arc> vfst;
  const auto s0 = vfst.AddState();
  const auto s1 = vfst.AddState();
  const auto s2 = vfst.AddState();
  vfst.SetStart(s0);
  vfst.SetFinal(s2, Arc::Weight::One());
  vfst.AddArc(s0, Arc(1, 1, 0.5f, s1));
  vfst.AddArc(s1, Arc(2, 2, 0.25f, s2));
  vfst.AddArc(s0, Arc(3, 3, 1.5f, s2));

  // 由 VectorFst 深拷贝出 LookAheadFst（扩展类型，构造期生成 matcher data）。
  fst::StdArcLookAheadFst lafst(vfst);
  Check(lafst.NumStates() == 3, "LookAheadFst: NumStates == 3");
  Check(lafst.Start() == s0, "LookAheadFst: Start == 0");
  Check(lafst.Final(s2) == Arc::Weight::One(), "LookAheadFst: final weight preserved");
  Check(lafst.Type() == "arc_lookahead", "LookAheadFst: Type == arc_lookahead");

  int narcs = 0;
  for (fst::ArcIterator<fst::StdArcLookAheadFst> aiter(lafst, s0); !aiter.Done();
       aiter.Next()) {
    ++narcs;
  }
  Check(narcs == 2, "LookAheadFst: state 0 exposes 2 arcs");

  // 扩展类型专用的 Matcher<MatcherFst<...>> 与 LookAheadMatcher<MatcherFst<...>>。
  fst::Matcher<fst::StdArcLookAheadFst> matcher(lafst, fst::MATCH_INPUT);
  matcher.SetState(s0);
  const bool found = matcher.Find(1);
  Check(found, "Matcher: Find(1) on state 0");
  Check(found && matcher.Value().nextstate == s1, "Matcher: arc 1 -> state 1");

  fst::LookAheadMatcher<fst::StdArcLookAheadFst> la_matcher(lafst, fst::MATCH_INPUT);
  la_matcher.SetState(s0);
  Check(la_matcher.LookAheadLabel(1), "LookAheadMatcher: LookAheadLabel(1) true");
  Check(!la_matcher.LookAheadLabel(99), "LookAheadMatcher: LookAheadLabel(99) false");

  // 3) 端到端：写出后经注册表读回（reader 来自扩展库）。
  const bool wrote = lafst.Write(path);
  Check(wrote, "LookAheadFst: Write() to disk");
  if (wrote) {
    std::unique_ptr<fst::Fst<Arc>> back(fst::Fst<Arc>::Read(path));
    Check(back != nullptr, "Fst<StdArc>::Read: resolves arc_lookahead via extension register");
    if (back) {
      Check(back->Type() == "arc_lookahead", "round-trip: type preserved");
      const auto *expanded = dynamic_cast<const fst::ExpandedFst<Arc> *>(back.get());
      Check(expanded != nullptr && expanded->NumStates() == 3,
            "round-trip: state count preserved");
    }
  }

  std::printf("HMBS_CONSUMER_ASSERTIONS={\"total\":%d,\"passed\":%d,\"failed\":%d}\n",
              g_total, g_total - g_failed, g_failed);
  if (g_failed != 0) {
    std::printf("FAIL lookahead consumer: %d/%d assertions failed\n", g_failed, g_total);
    return 1;
  }
  std::printf("PASS lookahead consumer: %d/%d assertions\n", g_total, g_total);
  return 0;
}
