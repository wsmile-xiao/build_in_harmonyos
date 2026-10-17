#include "CLucene.h"
#include "CLucene/util/CLStreams.h"
#include <iostream>

using namespace lucene::analysis;
using namespace lucene::analysis::standard;

int main(){
    WhitespaceAnalyzer ws;
    StandardAnalyzer stdAn;

    const TCHAR* text = _T("Hello World  TEST");
    // WhitespaceAnalyzer test via StringReader
    {
        lucene::util::StringReader reader(text);
        TokenStream* ts = ws.tokenStream(_T("field"), &reader);
        Token tok;
        int count = 0;
        while(ts->next(&tok)){
            count++;
        }
        _CLLDELETE(ts);
        std::cout << "WhitespaceAnalyzer tokens: " << count << std::endl;
        if(count != 3){
            std::cerr << "expected 3 tokens, got " << count << std::endl;
            return 1;
        }
    }

    {
        lucene::util::StringReader reader2(text);
        TokenStream* ts2 = stdAn.tokenStream(_T("field"), &reader2);
        Token tok;
        int count2 = 0;
        while(ts2->next(&tok)){
            count2++;
        }
        _CLLDELETE(ts2);
        std::cout << "StandardAnalyzer tokens: " << count2 << std::endl;
        if(count2 < 2){
            std::cerr << "StandardAnalyzer produced too few tokens" << std::endl;
            return 1;
        }
    }

    std::cout << "analyzer tests passed" << std::endl;
    return 0;
}
