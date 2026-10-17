/**
 * clucene-contribs 2.3.3.4 test_package 消费者测试。
 * 使用 contribs 公开 API 完成真实链路：GermanAnalyzer（contribs 分析器）
 * 建内存索引 → 检索 → 断言词干化命中。覆盖 contribs-lib/CLucene/analysis/de
 * 链路（GermanAnalyzer → GermanStemFilter → GermanStemmer）。
 */
#include "CLucene.h"
#include "CLucene/analysis/de/GermanAnalyzer.h"
#include "CLucene/config/repl_tchar.h"
#include "CLucene/config/repl_wchar.h"

#include <cstdio>
#include <cstring>

int main() {
    const int N = 6;
    {
        lucene::store::RAMDirectory ram;
        lucene::analysis::de::GermanAnalyzer an;
        lucene::index::IndexWriter writer(&ram, &an, true);

        // doc0 含德语名词 Bücher（GermanAnalyzer 词干化后为 buch），
        // 其余文档为普通英文词
        const TCHAR* docs[N] = {
            _T("Bücher'), und andere Wörter"),
            _T("common words only"),
            _T("another plain entry"),
            _T("more filler text here"),
            _T("unrelated vocabulary"),
            _T("last filler document"),
        };
        for (int i = 0; i < N; ++i) {
            lucene::document::Document doc;
            TCHAR id[16];
            _i64tot(i, id, 10);
            doc.add(*_CLNEW lucene::document::Field(
                _T("id"), id,
                lucene::document::Field::STORE_YES |
                    lucene::document::Field::INDEX_UNTOKENIZED));
            doc.add(*_CLNEW lucene::document::Field(
                _T("contents"), docs[i],
                lucene::document::Field::STORE_NO |
                    lucene::document::Field::INDEX_TOKENIZED));
            writer.addDocument(&doc);
        }
        writer.close();

        // 词干化后 buch 命中 doc0（Bücher→buch）
        lucene::search::Query* q =
            lucene::queryParser::QueryParser::parse(
                _T("buch"), _T("contents"), &an);
        lucene::search::IndexSearcher* searcher =
            _CLNEW lucene::search::IndexSearcher(&ram);
        lucene::search::Hits* hits = searcher->search(q);
        if (hits->length() != 1) {
            std::printf("FAIL: buch hits=%zu expected=1\n", hits->length());
            _CLLDELETE(hits);
            _CLLDELETE(q);
            searcher->close();
            _CLLDELETE(searcher);
            ram.close();
            return 1;
        }
        const TCHAR* got = hits->doc(0).get(_T("id"));
        if (got == NULL || _tcscmp(got, _T("0")) != 0) {
            std::printf("FAIL: expected doc id 0, got %s\n",
                        got ? "?" : "NULL");
            _CLLDELETE(hits);
            _CLLDELETE(q);
            searcher->close();
            _CLLDELETE(searcher);
            ram.close();
            return 1;
        }

        _CLLDELETE(hits);
        _CLLDELETE(q);
        searcher->close();
        _CLLDELETE(searcher);
        ram.close();
    }

    std::printf("clucene-contribs smoke: OK (GermanAnalyzer stem hit)\n");
    return 0;
}
