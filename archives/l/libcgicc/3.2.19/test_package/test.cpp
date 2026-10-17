#include <cgicc/CgiUtils.h>
#include <cgicc/FormEntry.h>
#include <cgicc/HTTPHTMLHeader.h>
#include <cgicc/HTTPCookie.h>

#include <iostream>
#include <sstream>
#include <string>

namespace {
int failures = 0;

void expect(bool condition, const char *message)
{
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        ++failures;
    }
}
}

int main()
{
    const std::string encoded = cgicc::form_urlencode("name=GNU cgicc&ok=yes");
    expect(encoded == "name%3DGNU+cgicc%26ok%3Dyes", "form_urlencode escapes reserved characters");
    expect(cgicc::form_urldecode(encoded) == "name=GNU cgicc&ok=yes", "form_urldecode reverses encoded data");

    const cgicc::FormEntry entry("library", "cgicc");
    expect(entry.getName() == "library", "FormEntry stores field name");
    expect(entry.getValue() == "cgicc", "FormEntry stores field value");

    cgicc::HTTPCookie cookie("session", "abc123");
    cookie.setMaxAge(60);
    cookie.setPath("/");
    expect(cookie.getName() == "session" && cookie.getValue() == "abc123", "HTTPCookie stores name and value");
    expect(cookie.getMaxAge() == 60 && cookie.getPath() == "/", "HTTPCookie stores attributes");

    std::ostringstream header;
    header << cgicc::HTTPHTMLHeader().setCookie(cookie);
    const std::string header_text = header.str();
    expect(header_text.find("Content-Type: text/html") != std::string::npos, "HTTPHTMLHeader renders content type");

    return failures == 0 ? 0 : 1;
}
