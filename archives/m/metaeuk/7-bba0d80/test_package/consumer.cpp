// metaeuk 7-bba0d80 consumer test (test_package)
//
// 上游无任何测试注册入口 ⇒ N_static=0：全树 add_test( / enable_testing /
// include(CTest) 命中 0/0/0，亦无 Makefile.am/configure.ac（无 automake
// TESTS）。另两处"测试形状"的东西都不是注册用例，按 R34/R51 不折算进用例数：
//   - lib/mmseqs/src/test/ 是 vendored MMseqs2 的上游手工自测 harness
//     （兼回归工具），35 个文件含 main 但只是自测程序；其唯一入口
//     add_subdirectory(test) 位于根 CMakeLists.txt:6 FORCE 的 FRAMEWORK_ONLY
//     与默认 0 的 HAVE_TESTS 双闸之内，本包自含构建下该子目录永不加入，
//     且 mmseqs_setup_test() 自身只 add_executable、不 add_test。
//   - tests/（metaeuk-regression 回归数据集）是 git 子模块，tag 包里只留空
//     目录、内容不随附；上游 azure-pipelines 靠克隆子模块 + -DHAVE_TESTS=1
//     外部驱动。
// 故按 R34/R51 以被测二进制的真实行为断言补位（5 项）：
//   1) 裸 `metaeuk`（无参）退出码 0 且输出含版本串 7-bba0d80
//      —— VERSION_OVERRIDE 生效。注：`--version` 不是合法子命令，会以非零
//      退出，故版本横幅取自裸调用（实测裸调用在非 tty / popen 下 rc=0 且
//      stdout 含 `metaeuk Version: 7-bba0d80`）。
//   2) `metaeuk -h` 退出码 0（命令枚举与帮助路径可用）
//   3) 非法参数以非零退出码结束（参数校验真实生效）
//   4a) `easy-predict` 合成 contigs/targets 端到端：退出码 0 且按实测产物名
//       predictions.fa.fas（及 .codon.fas/.gff/.headersMap.tsv）生成。
//       ⚠ 诚实口径：合成序列在零命中的内置比对库上无任何匹配，产物均为
//       0 字节。本断言只证明"基因预测工作流可跑通并产出规定文件"，
//       **不证明预测正确性**（端到端预测正确性需外部 target 数据库，
//       不在自含测试口径内）。
//   4b) `createdb` 自含往返（不依赖外部数据库）：合成 FASTA 建库退出码 0，
//       且序列库文件 db 与头文件 db_h **非空**。用以补上一条真正可证伪的
//       "非空产物"断言——若建库解析/写出坏掉，db/db_h 会是缺失或 0 字节。
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

namespace {

int run(const std::string& metaeuk, const std::string& args) {
    std::string cmd = metaeuk + " " + args + " >/dev/null 2>&1";
    return std::system(cmd.c_str());
}

// 文件字节数；不存在/不可读返回 -1（空文件返回 0）。
long filesize(const std::string& path) {
    std::ifstream f(path.c_str(), std::ios::binary | std::ios::ate);
    if (!f) {
        return -1;
    }
    return static_cast<long>(f.tellg());
}

}  // namespace

int main(int argc, char** argv) {
    std::string metaeuk = "metaeuk";
    if (argc > 1) {
        metaeuk = argv[1];
    }

    const char* dir = std::getenv("METAEUK_TEST_DIR");
    std::string work = dir ? dir : ".";

    // 1) 裸 metaeuk：退出码 0 且版本横幅含 7-bba0d80（VERSION_OVERRIDE 生效）
    {
        FILE* p = popen(metaeuk.c_str(), "r");
        if (!p) {
            std::cerr << "FAIL: cannot run bare metaeuk\n";
            return 1;
        }
        std::string out;
        char buf[256];
        while (fgets(buf, sizeof(buf), p)) {
            out += buf;
        }
        int rc = pclose(p);
        if (rc != 0) {
            std::cerr << "FAIL: bare metaeuk returned non-zero (rc=" << rc << ")\n";
            return 1;
        }
        if (out.find("7-bba0d80") == std::string::npos) {
            std::cerr << "FAIL: version banner missing 7-bba0d80, got: " << out << "\n";
            return 1;
        }
    }

    // 2) -h 帮助退出码 0
    if (run(metaeuk, "-h") != 0) {
        std::cerr << "FAIL: metaeuk -h returned non-zero\n";
        return 1;
    }

    // 3) 非法参数必须非零退出（真实参数校验）
    if (run(metaeuk, "--no-such-option-xyz") == 0) {
        std::cerr << "FAIL: invalid option unexpectedly succeeded\n";
        return 1;
    }

    // 4a) easy-predict 端到端（合成数据）——仅证工作流跑通 + 规定产物生成
    {
        std::ofstream contigs(work + "/contigs.fa");
        // 单条 contig：3 段外显子（各 90nt），中间以 60nt 内含子间隔
        contigs << ">contig1 synthetic\n";
        contigs << "ATGGCTTCTATCAGCGGTTTCAAAATCATTGCAATGCTGGGCTCTGGTATCTTCGCTGGT"
                   "GGCTTCGTTATCGGTATCGGTTCTGGCTCTATCGAA\n";
        contigs << "TAAGCGGCGCGTAACGTATCGAATTAAGCGCGCGTTAACGCGCGTATATATCGCGCGTA"
                   "TTAAATGCGCGCGTAATTTAAGCGCGCGCGCGTAATAA\n";
        contigs << "ATGGCTTCTATCAGCGGTTTCAAAATCATTGCAATGCTGGGCTCTGGTATCTTCGCTGGT"
                   "GGCTTCGTTATCGGTATCGGTTCTGGCTCTATCGAA\n";
        std::ofstream targets(work + "/targets.fa");
        targets << ">target1 synthetic protein\n";
        targets << "MASMSVSKSLAMLGLWYLRLASLIGIGSALELA\n";
    }
    std::string preds = work + "/predictions.fa";
    std::remove((preds + ".fas").c_str());
    std::remove((preds + ".codon.fas").c_str());
    std::remove((preds + ".gff").c_str());
    std::remove((preds + ".headersMap.tsv").c_str());
    if (run(metaeuk, "easy-predict " + work + "/contigs.fa " + work +
                         "/targets.fa " + preds + " " + work + "/tmp --threads 2") != 0) {
        std::cerr << "FAIL: easy-predict returned non-zero\n";
        return 1;
    }
    // 实测产物名带 MMseqs2 风格后缀（predictions.fa.fas 等）；裸前缀文件不生成。
    if (filesize(preds + ".fas") < 0) {
        std::cerr << "FAIL: easy-predict product missing: " << preds << ".fas\n";
        return 1;
    }

    // 4b) createdb 自含往返（不依赖外部 target 数据库）——证真非空产物
    {
        std::ofstream dbin(work + "/db_input.fa");
        dbin << ">seq1 synthetic protein\n"
                "MASMSVSKSLAMLGLWYLRLASLIGIGSALELAKEVQLVGAPSVSRTQGKWALGVNVGKGKVTWRGDAVA\n";
        dbin << ">seq2 synthetic protein\n"
                "MKFIISLLIFLVFSSTLAVVSEFKLGIAIGIAILSAFKSGDLVNWVSATTPPMSVTVLVATLVIGI\n";
    }
    std::string db = work + "/metadb";
    std::remove(db.c_str());
    std::remove((db + "_h").c_str());
    if (run(metaeuk, "createdb " + work + "/db_input.fa " + db) != 0) {
        std::cerr << "FAIL: createdb returned non-zero\n";
        return 1;
    }
    // createdb 产物按实测为平面文件：db=序列库、db_h=头文件，均须非空。
    if (filesize(db) <= 0) {
        std::cerr << "FAIL: createdb sequence file empty/missing: " << db << "\n";
        return 1;
    }
    if (filesize(db + "_h") <= 0) {
        std::cerr << "FAIL: createdb header file empty/missing: " << db << "_h\n";
        return 1;
    }

    std::cout << "consumer test passed: 5 assertions OK "
                 "(bare-version / -h / bad-arg / easy-predict-products / createdb-nonempty)\n";
    return 0;
}
