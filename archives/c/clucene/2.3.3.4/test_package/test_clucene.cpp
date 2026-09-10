#include "CLucene.h"
#include <iostream>
#include <cassert>

using namespace lucene::index;
using namespace lucene::analysis;
using namespace lucene::store;
using namespace lucene::document;
using namespace lucene::search;
using namespace lucene::queryParser;

int main(){
    RAMDirectory ram;
    WhitespaceAnalyzer analyzer;

    IndexWriter* writer = _CLNEW IndexWriter(&ram, &analyzer, true);
    writer->setMaxFieldLength(0x7FFFFFFFL);
    writer->setUseCompoundFile(false);

    Document doc1;
    doc1.add(*_CLNEW Field(_T("contents"), _T("hello world"), Field::STORE_YES | Field::INDEX_TOKENIZED));
    doc1.add(*_CLNEW Field(_T("path"), _T("/a.txt"), Field::STORE_YES | Field::INDEX_UNTOKENIZED));
    writer->addDocument(&doc1);

    Document doc2;
    doc2.add(*_CLNEW Field(_T("contents"), _T("foo bar"), Field::STORE_YES | Field::INDEX_TOKENIZED));
    doc2.add(*_CLNEW Field(_T("path"), _T("/b.txt"), Field::STORE_YES | Field::INDEX_UNTOKENIZED));
    writer->addDocument(&doc2);

    writer->setUseCompoundFile(true);
    writer->optimize();
    writer->close();
    _CLLDELETE(writer);

    IndexSearcher s(&ram);
    Query* q = QueryParser::parse(_T("hello"), _T("contents"), &analyzer);
    Hits* hits = s.search(q);

    int len = hits->length();
    std::cout << "hits: " << len << std::endl;
    if(len != 1){
        std::cerr << "expected 1 hit, got " << len << std::endl;
        return 1;
    }
    Document* d = &hits->doc(0);
    const TCHAR* p = d->get(_T("path"));
    if(p == NULL){
        std::cerr << "path field missing" << std::endl;
        return 1;
    }
    std::cout << "first hit path retrieved" << std::endl;
    _CLLDELETE(hits);
    _CLLDELETE(q);
    s.close();
    ram.close();

    std::cout << "clucene RAMDirectory index+search passed" << std::endl;
    return 0;
}
