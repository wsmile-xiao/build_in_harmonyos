// test_package/consumer.cpp — kmc 3.2.4 包消费验证（KMC::Runner API）
//
// 用官方发行的唯一头文件 include/kmc_runner.h 编程式驱动两阶段计数，
// 断言值与上游 .github/workflows/main.yml "KMC single read, k=28, ci=1" 步骤
// 的实测输出一致（single_read.fq, k=28, ci=1）：
//   Total no. of k-mers : 70
//   Total no. of reads  : 1
//   No. of unique k-mers: 40
// 用法: consumer_bin <input.fastq> <tmp_dir> <output_db>
#include <kmc_runner.h>

#include <cstdio>
#include <string>

static int fail(const char* what, unsigned long long got, unsigned long long want)
{
    std::fprintf(stderr, "FAIL: %s = %llu (expected %llu)\n", what, got, want);
    return 1;
}

int main(int argc, char** argv)
{
    if (argc < 4)
    {
        std::fprintf(stderr, "usage: %s <input.fastq> <tmp_dir> <out_db>\n", argv[0]);
        return 64;
    }

    try
    {
        KMC::Stage1Params p1;
        p1.SetInputFiles({std::string(argv[1])})
          .SetTmpPath(argv[2])
          .SetKmerLen(28)
          .SetNThreads(2)
          .SetMaxRamGB(2)
          .SetInputFileType(KMC::InputFileType::FASTQ);

        KMC::Runner runner;
        KMC::Stage1Results r1 = runner.RunStage1(p1);

        KMC::Stage2Params p2;
        p2.SetOutputFileName(argv[3])
          .SetCutoffMin(1)
          .SetNThreads(2)
          .SetMaxRamGB(2);
        KMC::Stage2Results r2 = runner.RunStage2(p2);

        if (r1.nSeqences != 1)
            return fail("stage1.nSeqences", (unsigned long long)r1.nSeqences, 1);
        if (r2.nTotalKmers != 70)
            return fail("stage2.nTotalKmers", (unsigned long long)r2.nTotalKmers, 70);
        if (r2.nUniqueKmers != 40)
            return fail("stage2.nUniqueKmers", (unsigned long long)r2.nUniqueKmers, 40);

        std::printf(
            "PASS consumer: nSeqences=%llu nTotalKmers=%llu nUniqueKmers=%llu "
            "nBelowCutoffMin=%llu\n",
            (unsigned long long)r1.nSeqences,
            (unsigned long long)r2.nTotalKmers,
            (unsigned long long)r2.nUniqueKmers,
            (unsigned long long)r2.nBelowCutoffMin);
        return 0;
    }
    catch (const std::exception& e)
    {
        std::fprintf(stderr, "FAIL: exception: %s\n", e.what());
        return 70;
    }
}
