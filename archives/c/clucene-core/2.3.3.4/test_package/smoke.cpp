/**
 * clucene-core 2.3.3.4 test_package 消费者测试。
 * 使用公开 API 完成真实链路：建内存索引 → 检索 → 断言命中与存储字段回读。
 * 覆盖 IndexWriter / Analyzer / Document / Field / IndexReader /
 * QueryParser / IndexSearcher / Hits。
 *
 * 分析器语义说明：SimpleAnalyzer 为 LetterTokenizer（连续字母切分，
 * "w3" 会被切成 "w"），需按词检索故用 WhitespaceAnalyzer。
 * 生命周期：搜索期对象（Query/Hits/IndexSearcher）经 _CLNEW 堆分配并
 * _CLLDELETE 释放（CLucene 基于引用计数，禁止对栈对象 _CLLDELETE）。
 */
#include "CLucene.h"
#include "CLucene/config/repl_tchar.h"
#include "CLucene/config/repl_wchar.h"

#include <cstdio>
#include <cstring>

int main() {
    const int N = 20;
    {
        lucene::store::RAMDirectory ram;
        lucene::analysis::WhitespaceAnalyzer an;
        lucene::index::IndexWriter writer(&ram, &an, true);

        // doc i 的 contents = "w0 w1 ... w{i}"（词 w{k} 出现在 doc k..N-1）
        for (int i = 0; i < N; ++i) {
            lucene::document::Document doc;

            TCHAR id[16];
            _i64tot(i, id, 10);
            doc.add(*_CLNEW lucene::document::Field(
                _T("id"), id,
                lucene::document::Field::STORE_YES |
                    lucene::document::Field::INDEX_UNTOKENIZED));

            TCHAR content[1024];
            content[0] = 0;
            for (int k = 0; k <= i; ++k) {
                TCHAR term[16];
                _sntprintf(term, 16, _T("w%d "), k);
                _tcsncat(content, term, 16);
            }
            doc.add(*_CLNEW lucene::document::Field(
                _T("contents"), content,
                lucene::document::Field::STORE_NO |
                    lucene::document::Field::INDEX_TOKENIZED));

            writer.addDocument(&doc);
        }
        writer.close();

        // 1) IndexReader 文档数
        lucene::index::IndexReader* reader =
            lucene::index::IndexReader::open(&ram);
        if (reader->numDocs() != N) {
            std::printf("FAIL: numDocs=%d expected=%d\n", reader->numDocs(), N);
            reader->close();
            _CLDELETE(reader);
            return 1;
        }
        reader->close();
        _CLDELETE(reader);

        // 2) QueryParser 检索 w3 → 应命中 doc 3..19 共 17 篇
        lucene::search::Query* q =
            lucene::queryParser::QueryParser::parse(_T("w3"), _T("contents"), &an);
        lucene::search::IndexSearcher* searcher =
            _CLNEW lucene::search::IndexSearcher(&ram);
        lucene::search::Hits* hits = searcher->search(q);
        if (hits->length() != N - 3) {
            std::printf("FAIL: hits=%zu expected=%d\n", hits->length(), N - 3);
            _CLLDELETE(hits);
            _CLLDELETE(q);
            searcher->close();
            _CLLDELETE(searcher);
            ram.close();
            return 1;
        }

        // 3) 存储字段回读：第一命中应为 doc 3，id="3"
        const TCHAR* got = hits->doc(0).get(_T("id"));
        if (got == NULL || _tcscmp(got, _T("3")) != 0) {
            std::printf("FAIL: stored id mismatch\n");
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

    std::printf("clucene smoke: OK (%d docs indexed & searched)\n", N);
    return 0;
}
