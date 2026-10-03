// Consumer test for the sptag Conan package (OHOS aarch64).
// Exercises the real public C++ API end to end: build a KDT and a BKT
// index over synthetic float vectors, save/load the index, search it,
// and verify the top-1 hit of every query. Returns nonzero on any failure.
#include "inc/Core/VectorIndex.h"
#include "inc/Core/Common/CommonUtils.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const char* what) {
    ++g_checks;
    if (ok) {
        std::printf("[PASS] %s\n", what);
    } else {
        ++g_failed;
        std::printf("[FAIL] %s\n", what);
    }
}

struct DataSet {
    std::vector<float> vec;
    std::vector<char> meta;
    std::vector<std::uint64_t> metaoffset;
    SPTAG::SizeType n;
    SPTAG::DimensionType m;
};

DataSet make_data(SPTAG::SizeType n, SPTAG::DimensionType m) {
    DataSet d;
    d.n = n;
    d.m = m;
    for (SPTAG::SizeType i = 0; i < n; i++)
        for (SPTAG::DimensionType j = 0; j < m; j++)
            d.vec.push_back(static_cast<float>(i));
    for (SPTAG::SizeType i = 0; i < n; i++) {
        d.metaoffset.push_back(static_cast<std::uint64_t>(d.meta.size()));
        std::string a = std::to_string(i);
        for (char c : a) d.meta.push_back(c);
    }
    d.metaoffset.push_back(static_cast<std::uint64_t>(d.meta.size()));
    return d;
}

void make_sets(const DataSet& d,
               std::shared_ptr<SPTAG::VectorSet>& vecset,
               std::shared_ptr<SPTAG::MetadataSet>& metaset) {
    vecset = std::shared_ptr<SPTAG::VectorSet>(new SPTAG::BasicVectorSet(
        SPTAG::ByteArray(reinterpret_cast<std::uint8_t*>(
                             const_cast<float*>(d.vec.data())),
                         sizeof(float) * d.n * d.m, false),
        SPTAG::GetEnumValueType<float>(), d.m, d.n));
    metaset = std::shared_ptr<SPTAG::MetadataSet>(new SPTAG::MemMetadataSet(
        SPTAG::ByteArray(reinterpret_cast<std::uint8_t*>(
                             const_cast<char*>(d.meta.data())),
                         d.meta.size() * sizeof(char), false),
        SPTAG::ByteArray(reinterpret_cast<std::uint8_t*>(
                             const_cast<std::uint64_t*>(d.metaoffset.data())),
                         d.metaoffset.size() * sizeof(std::uint64_t), false),
        d.n));
}

std::shared_ptr<SPTAG::VectorIndex> build_index(SPTAG::IndexAlgoType algo,
                                                const DataSet& d) {
    std::shared_ptr<SPTAG::VectorSet> vecset;
    std::shared_ptr<SPTAG::MetadataSet> metaset;
    make_sets(d, vecset, metaset);
    std::shared_ptr<SPTAG::VectorIndex> index =
        SPTAG::VectorIndex::CreateInstance(algo, SPTAG::GetEnumValueType<float>());
    if (!index) return index;
    index->SetParameter("DistCalcMethod", "L2");
    index->SetParameter("NumberOfThreads", "1");
    if (SPTAG::ErrorCode::Success != index->BuildIndex(vecset, metaset))
        return nullptr;
    return index;
}

bool search_self(const std::shared_ptr<SPTAG::VectorIndex>& index,
                 const DataSet& d, SPTAG::SizeType query_id) {
    std::vector<float> q(d.m, static_cast<float>(query_id));
    SPTAG::QueryResult res(q.data(), 1, true);
    index->SearchIndex(res);
    if (res.GetResult(0) == nullptr) return false;
    if (res.GetResult(0)->VID != static_cast<SPTAG::SizeType>(query_id))
        return false;
    return std::fabs(res.GetResult(0)->Dist) < 1e-3f;
}

}  // namespace

int main() {
    DataSet d = make_data(200, 8);

    std::shared_ptr<SPTAG::VectorIndex> kdt =
        build_index(SPTAG::IndexAlgoType::KDT, d);
    check(kdt != nullptr, "KDT BuildIndex succeeds");
    check(SPTAG::ErrorCode::Success == kdt->SaveIndex("testidx_kdt"),
          "KDT SaveIndex succeeds");
    std::shared_ptr<SPTAG::VectorIndex> loaded;
    check(SPTAG::ErrorCode::Success ==
              SPTAG::VectorIndex::LoadIndex("testidx_kdt", loaded),
          "KDT LoadIndex succeeds");
    check(loaded != nullptr, "KDT loaded index is usable");
    check(search_self(loaded, d, 10), "KDT query 10 finds itself at dist 0");
    check(search_self(loaded, d, 100), "KDT query 100 finds itself at dist 0");
    check(search_self(loaded, d, 199), "KDT query 199 finds itself at dist 0");

    std::shared_ptr<SPTAG::VectorIndex> bkt =
        build_index(SPTAG::IndexAlgoType::BKT, d);
    check(bkt != nullptr, "BKT BuildIndex succeeds");
    check(search_self(bkt, d, 0), "BKT query 0 finds itself at dist 0");
    check(search_self(bkt, d, 150), "BKT query 150 finds itself at dist 0");
    check(bkt->GetFeatureDim() == 8, "BKT feature dim is 8");
    check(bkt->GetNumSamples() == 200, "BKT sample count is 200");

    std::printf("checks: %d, failed: %d\n", g_checks, g_failed);
    std::printf(g_failed == 0 ? "ALL CHECKS PASSED\n" : "CHECKS FAILED\n");
    return g_failed == 0 ? 0 : 1;
}
