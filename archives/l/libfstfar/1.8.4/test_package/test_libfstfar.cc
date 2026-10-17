// libfstfar 1.8.4 HarmonyOS consumer test (test_package).
//
// 这个程序是**真消费者**：它 include 本包安装的 FAR 公共头文件，链接本包安装的
// libfstfar，并在真机上执行。两条链路各自独立可归因：
//   A. 直接调用 libfstfar 自己的编译单元导出的强符号
//      —— fst::IsSTList() / fst::IsSTTable() 定义在 extensions/far/stlist.cc、sttable.cc，
//         它们只存在于 libfstfar.a/.so，链接期缺失即失败（证明链接的是本包产物）；
//   B. 走 FAR 公共 API（FarWriter / FarReader）把一个 VectorFst<StdArc> 写进 STList 档案再读回比对
//      —— 这是 libfstfar 的实际功能面。
//
// 检查计数由程序自己打印（HMBS_CONSUMER_CHECKS=n），与 shell 检查分开计。
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <memory>
#include <string>

#include <fst/extensions/far/far.h>
#include <fst/extensions/far/stlist.h>
#include <fst/extensions/far/sttable.h>
#include <fst/float-weight.h>
#include <fst/util.h>
#include <fst/vector-fst.h>

namespace {

int checks_run = 0;
int checks_failed = 0;

void Check(bool ok, const char *what) {
  ++checks_run;
  if (!ok) {
    ++checks_failed;
    std::cerr << "CHECK-FAIL: " << what << "\n";
  } else {
    std::cerr << "check-ok: " << what << "\n";
  }
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 2) {
    std::cerr << "usage: test_libfstfar <archive-path>\n";
    return 2;
  }
  const std::string path = argv[1];
  std::remove(path.c_str());

  // ---- A. libfstfar 自身编译单元导出的符号（无此库则链接期失败） ----
  Check(!fst::IsSTList(path), "IsSTList() is false on a nonexistent path (symbol from stlist.cc)");
  Check(!fst::IsSTTable(path), "IsSTTable() is false on a nonexistent path (symbol from sttable.cc)");

  // ---- B. FAR 公共 API：写一个 2 状态 FST 进 STList 档案 ----
  fst::VectorFst<fst::StdArc> fst;
  const auto s0 = fst.AddState();
  const auto s1 = fst.AddState();
  fst.SetStart(s0);
  fst.SetFinal(s1, fst::StdArc::Weight(0.5f));
  fst.AddArc(s0, fst::StdArc(1, 1, fst::StdArc::Weight(0.25f), s1));
  Check(fst.NumStates() == 2, "source FST has 2 states");

  {
    std::unique_ptr<fst::FarWriter<fst::StdArc>> writer(
        fst::FarWriter<fst::StdArc>::Create(path, fst::FarType::STLIST));
    Check(writer != nullptr, "FarWriter<StdArc>::Create(STLIST) returned a writer");
    if (!writer) return 1;
    writer->Add("entry1", fst);
    Check(!writer->Error(), "FarWriter::Add(\"entry1\") reported no error");
  }

  Check(fst::IsSTList(path), "archive written by FarWriter is recognized by IsSTList()");
  Check(!fst::IsSTTable(path), "archive written by FarWriter is not an STTable");

  {
    std::unique_ptr<fst::FarReader<fst::StdArc>> reader(
        fst::FarReader<fst::StdArc>::Open(path));
    Check(reader != nullptr, "FarReader<StdArc>::Open() reopened the archive");
    if (!reader) return 1;
    // STList 是**顺序**档案，FarReader::Find() 对它不支持（上游 STListReader::Find 直接
    // LOG(FATAL) "Operation not supported"），因此这里走顺序迭代：
    // Done/GetKey/GetFst 取首条 → Next → Done 确认只有一条。
    Check(!reader->Done(), "freshly opened archive is positioned at the first entry");
    if (!reader->Done()) {
      Check(reader->GetKey() == "entry1", "first entry key is entry1");
      const fst::Fst<fst::StdArc> *readback = reader->GetFst();
      Check(readback != nullptr, "FarReader::GetFst() returned the stored FST");
      if (readback) {
        Check(fst::CountStates(*readback) == 2 && readback->NumArcs(s0) == 1,
              "readback FST has 2 states and 1 outgoing arc (registry-based Fst::Read path)");
        Check(readback->Start() == s0, "readback FST start state preserved");
      }
      reader->Next();
    }
    Check(reader->Done(), "archive contains exactly one entry");
  }

  std::cout << "HMBS_CONSUMER_CHECKS=" << checks_run
            << " HMBS_CONSUMER_FAILED=" << checks_failed << std::endl;
  if (checks_failed != 0) {
    std::cerr << "consumer test FAILED (" << checks_failed << "/" << checks_run << ")\n";
    return 1;
  }
  std::cout << "PASS libfstfar consumer (linked libfstfar, FAR round trip)" << std::endl;
  return 0;
}
