// test_package 消费者用例：通过 libpar2 公开 API 完成一次
// "PAR2 创建 → PAR2 校验" 闭环，验证第三方上层组件可正常编译、链接、
// 调用并观察到正确结果（R34：禁止只打印字符串的空壳测试）。
//
// 使用公开安装产物：
//   include/libpar2/par2cmdline.h（CommandLine/Result/枚举）
//   链接 libpar2（libpar2.a）
#include <libpar2/par2cmdline.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

// 等待脚本轮询的文件：非空且内容为 "ok" 表示运行完成
#define CREATED_MARKER "libpar2.consumer.created"

static bool write_marker(const char* path) {
  FILE* f = fopen(path, "w");
  if (!f) return false;
  fputs("ok", f);
  fclose(f);
  return true;
}

static bool file_exists(const char* path) {
  FILE* f = fopen(path, "r");
  if (!f) return false;
  fclose(f);
  return true;
}

int main(void) {
  // 1) 准备一个已知内容的数据文件作为 PAR2 源
  const char* datafile = "consumer-data.bin";
  {
    FILE* f = fopen(datafile, "wb");
    if (!f) { std::printf("FAIL: cannot create %s\n", datafile); return 1; }
    for (int i = 0; i < 4096; ++i) {
      unsigned char c = (unsigned char)(i * 31 + 7);
      if (fwrite(&c, 1, 1, f) != 1) { fclose(f); return 1; }
    }
    fclose(f);
  }

  // 2) 创建 PAR2 恢复文件（公开 API：CommandLine::Parse + Par2Creator）
  const char* par2file = "consumer-data.par2";
  char* argv_create[] = {
    const_cast<char*>("consumer-test"),
    const_cast<char*>("c"),        // opCreate
    const_cast<char*>("-b16"),     // block count
    const_cast<char*>("-r10"),     // 10% redundancy
    const_cast<char*>(par2file),
    const_cast<char*>(datafile),
  };
  {
    CommandLine cmd;
    if (!cmd.Parse(6, argv_create)) {
      std::printf("FAIL: CommandLine::Parse(create) failed\n");
      return 1;
    }
    Par2Creator creator;
    Result r = creator.Process(cmd);
    std::printf("Par2Creator::Process -> %d\n", (int)r);
    if (r != eSuccess) {
      std::printf("FAIL: PAR2 create returned %d (expected eSuccess=0)\n", (int)r);
      return 1;
    }
  }
  if (!file_exists(par2file)) {
    std::printf("FAIL: %s was not created\n", par2file);
    return 1;
  }
  std::printf("PASS: PAR2 file created: %s\n", par2file);

  // 3) 校验 PAR2（公开 API：CommandLine::Parse + Par2Repairer, dorepair=false）
  //    注意：Par2Repairer::Process 的前置加载步骤（LoadPacketsFromFile 等）
  //    在上游 0.2 中位于 PreProcess()，直接调用 Process() 会因 mainpacket
  //    为空而崩溃（实测 SegFault），必须先 PreProcess 再 Process。
  char* argv_verify[] = {
    const_cast<char*>("consumer-test"),
    const_cast<char*>("v"),        // opVerify
    const_cast<char*>(par2file),
    const_cast<char*>(datafile),
  };
  {
    CommandLine cmd;
    if (!cmd.Parse(4, argv_verify)) {
      std::printf("FAIL: CommandLine::Parse(verify) failed\n");
      return 1;
    }
    Par2Repairer repairer;
    Result pr = repairer.PreProcess(cmd);
    std::printf("Par2Repairer::PreProcess -> %d\n", (int)pr);
    if (pr != eSuccess) {
      std::printf("FAIL: PAR2 PreProcess returned %d (expected eSuccess=0)\n", (int)pr);
      return 1;
    }
    Result r = repairer.Process(cmd, false);  // verify only
    std::printf("Par2Repairer::Process(verify) -> %d\n", (int)r);
    if (r != eSuccess) {
      std::printf("FAIL: PAR2 verify returned %d (expected eSuccess=0)\n", (int)r);
      return 1;
    }
  }
  std::printf("PASS: PAR2 verify reported all files intact\n");

  // 4) 消费者观察到的可执行结果：创建产物存在 + 校验 eSuccess
  if (!write_marker(CREATED_MARKER)) {
    std::printf("FAIL: cannot write marker %s\n", CREATED_MARKER);
    return 1;
  }
  std::printf("CONSUMER-OK: libpar2 create+verify round-trip succeeded\n");
  return 0;
}