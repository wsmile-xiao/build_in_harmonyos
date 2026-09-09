#include <cgicc/Cgicc.h>
#include <cgicc/CgiEnvironment.h>
#include <cgicc/HTMLDoctype.h>
#include <cgicc/HTTPHTMLHeader.h>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    // 构造上下文：要求无 CGI 环境时构造函数仍可用（默认 CgiInput）
    cgicc::Cgicc cgi;

    // 调用被测库 API：CgiEnvironment
    const cgicc::CgiEnvironment& env = cgi.getEnvironment();
    std::string method = env.getRequestMethod();
    // CGI 环境变量缺省为空字符串，此处只验证 API 可调用、返回可读
    std::cout << "request_method='" << method << "'" << std::endl;

    // 调用被测库 API：HTMLDoctype（MStreamable 渲染）
    cgicc::HTMLDoctype doctype(cgicc::HTMLDoctype::eHTML5);
    std::ostringstream oss;
    oss << doctype;
    if (oss.str().empty()) {
        std::cerr << "FAIL: HTMLDoctype render empty" << std::endl;
        return 1;
    }
    std::cout << "doctype='" << oss.str() << "'" << std::endl;

    // 调用被测库 API：HTTPHTMLHeader
    cgicc::HTTPHTMLHeader header;
    std::ostringstream hss;
    hss << header;
    if (hss.str().empty()) {
        std::cerr << "FAIL: HTTPHTMLHeader render empty" << std::endl;
        return 1;
    }
    std::cout << "header='" << hss.str() << "'" << std::endl;

    std::cout << "cgicc consumer test: PASS" << std::endl;
    return 0;
}