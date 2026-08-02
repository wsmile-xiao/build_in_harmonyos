/* eckit 2.0.7 真实功能断言。
 *
 * 三条，都是可手算/可对照标准的纯本地计算：
 *   ① MD5 —— 对 RFC 1321 的标准测试向量断言，摘要是查得到的定值
 *   ② Tokenizer —— 切分后逐个 token 比对
 *   ③ **AEC 压缩往返** —— 这条是特意选的：eckit 的 AEC feature 要 libaec 1.1.4+，
 *      而 libaec/1.1.7 正是本仓上一批做的包。只测 MD5/Tokenizer 的话，
 *      libaec 没接上也照样全绿，等下游读 AEC 压缩数据才炸（与 hdf5 的 szip 判据同理）。
 *
 * 不用 dlopen 探针：解析到符号不等于函数能用。
 */
#include <eckit/eckit_version.h>
#include <eckit/utils/MD5.h>
#include <eckit/utils/Tokenizer.h>
#include <eckit/utils/Compressor.h>
#include <eckit/io/Buffer.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <memory>

static int test_version()
{
    /* 宏名是**小写** eckit_VERSION_STR（见 src/eckit/eckit_version.h.in），
     * 不是常见的全大写 ECKIT_ 风格 —— 按惯例猜会编不过。 */
    const char* v = eckit_version();
    std::printf("eckit 版本: %s / 宏 %s / int %u\n",
                v ? v : "(null)", eckit_VERSION_STR, eckit_version_int());
    if (!v || std::strlen(v) == 0) { std::printf("FAIL 版本号为空\n"); return 1; }
    if (std::strncmp(v, "2.0.7", 5) != 0) {
        std::printf("FAIL 版本 %s 不是 2.0.7\n", v); return 1;
    }
    /* 运行期函数与编译期宏必须一致 —— 不一致说明装出来的头与库不是同一次构建的，
     * 那是包本身的缺陷（混了两个版本），只比对其中一个发现不了。 */
    if (std::strcmp(v, eckit_VERSION_STR) != 0) {
        std::printf("FAIL 运行期 %s 与编译期宏 %s 不一致（头与库版本错配）\n",
                    v, eckit_VERSION_STR);
        return 1;
    }
    if (eckit_version_int() != 20007u) {
        std::printf("FAIL version_int %u != 20007\n", eckit_version_int()); return 1;
    }
    return 0;
}

static int test_md5()
{
    /* RFC 1321 的标准测试向量 —— 摘要是定值，不是"跑出来什么算什么"。 */
    struct { const char* in; const char* want; } cases[] = {
        {"",     "d41d8cd98f00b204e9800998ecf8427e"},
        {"abc",  "900150983cd24fb0d6963f7d28e17f72"},
        {"message digest", "f96b697d7cb7938d525a2f31aaf161d0"},
    };
    for (auto& c : cases) {
        eckit::MD5 h;
        h.add(std::string(c.in));
        std::string got = h.digest();
        if (got != c.want) {
            std::printf("FAIL MD5(\"%s\") = %s，期望 %s\n", c.in, got.c_str(), c.want);
            return 1;
        }
    }
    std::printf("MD5 OK: 3 个 RFC 1321 标准向量全部匹配\n");
    return 0;
}

static int test_tokenizer()
{
    eckit::Tokenizer parse(":");
    std::vector<std::string> out;
    parse("a:bb:ccc", out);
    if (out.size() != 3) { std::printf("FAIL token 数 %zu != 3\n", out.size()); return 1; }
    if (out[0] != "a" || out[1] != "bb" || out[2] != "ccc") {
        std::printf("FAIL token 内容: [%s][%s][%s]\n",
                    out[0].c_str(), out[1].c_str(), out[2].c_str());
        return 1;
    }
    std::printf("Tokenizer OK: \"a:bb:ccc\" -> 3 个 token 逐个一致\n");
    return 0;
}

static int test_aec_roundtrip()
{
    /* eckit 的 AEC feature 依赖 libaec —— 本仓上一批做的 libaec/1.1.7。
     * 若没接上，CompressorFactory 里就没有 "aec" 这个 builder，下面会抛异常。 */
    const size_t N = 4096;
    std::vector<char> src(N);
    for (size_t i = 0; i < N; i++) src[i] = static_cast<char>(i / 32);   /* 高冗余，应能压缩 */

    std::unique_ptr<eckit::Compressor> c;
    try {
        c.reset(eckit::CompressorFactory::instance().build("aec"));
    } catch (std::exception& e) {
        std::printf("FAIL 取不到 aec 压缩器（libaec 未接入）: %s\n", e.what());
        return 1;
    }
    if (!c) { std::printf("FAIL aec 压缩器为空\n"); return 1; }

    eckit::Buffer enc(N * 2);
    size_t elen = c->compress(src.data(), N, enc);
    if (elen == 0 || elen >= N) {
        std::printf("FAIL AEC 未压缩: %zu -> %zu 字节\n", N, elen);
        return 1;
    }

    eckit::Buffer dec(N);
    c->uncompress(enc.data(), elen, dec, N);
    if (std::memcmp(src.data(), dec.data(), N) != 0) {
        std::printf("FAIL AEC 往返数据不一致\n");
        return 1;
    }
    std::printf("AEC 往返 OK: %zu -> %zu 字节（压至 %.1f%%），解码逐字节一致 —— libaec 已接入\n",
                N, elen, 100.0 * (double)elen / (double)N);
    return 0;
}

int main()
{
    if (test_version())       return 1;
    if (test_md5())           return 1;
    if (test_tokenizer())     return 1;
    if (test_aec_roundtrip()) return 1;
    std::printf("eckit 2.0.7: 全部断言通过\n");
    return 0;
}
