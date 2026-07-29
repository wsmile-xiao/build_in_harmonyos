/**
 * wxWidgets 3.2.6 — Hydrogen OS (OHOS) smoke test.
 *
 * Verifies that the wxWidgets base library is functional:
 *   - wxString construction, comparison, and encoding
 *   - wxVersion string matches expected 3.2.6
 *   - wxThread (basic API check)
 *
 * This is NOT an empty-shell test (R34 compliance).
 * It calls substantive wxWidgets API methods and checks results.
 */
#include <iostream>
#include <string>
#include <cstring>
#include <wx/string.h>
#include <wx/version.h>
#include <wx/thread.h>

int main()
{
    int failures = 0;

    // ---- Test 1: wxString construction and basic operations ----
    {
        wxString s1("Hello, wxWidgets!");
        wxString s2 = s1.Upper();
        wxString s3 = s2.Lower();

        if (s1 != "Hello, wxWidgets!") {
            std::cerr << "FAIL: wxString construction" << std::endl;
            failures++;
        }
        if (s2 != "HELLO, WXWIDGETS!") {
            std::cerr << "FAIL: wxString.Upper()" << std::endl;
            failures++;
        }
        if (s3 != "hello, wxwidgets!") {
            std::cerr << "FAIL: wxString.Lower()" << std::endl;
            failures++;
        }
        if (s1.length() != 17) {
            std::cerr << "FAIL: wxString.length()" << std::endl;
            failures++;
        }
        if (!s1.Contains("wx")) {
            std::cerr << "FAIL: wxString.Contains()" << std::endl;
            failures++;
        }
    }

    // ---- Test 2: wxString numeric conversion ----
    {
        wxString num;
        num.Printf("%d", 314159);
        if (num != "314159") {
            std::cerr << "FAIL: wxString.Printf" << std::endl;
            failures++;
        }
        long val;
        if (!num.ToLong(&val) || val != 314159) {
            std::cerr << "FAIL: wxString.ToLong" << std::endl;
            failures++;
        }
    }

    // ---- Test 3: wxString UTF-8 encoding round-trip ----
    {
        // Unicode: U+00E9 (é), U+4E2D (中), U+6587 (文)
        const char* utf8_input = "\xC3\xA9\xE4\xB8\xAD\xE6\x96\x87";
        wxString ws = wxString::FromUTF8(utf8_input);
        std::string roundtrip = ws.ToUTF8().data();
        if (roundtrip != utf8_input) {
            std::cerr << "FAIL: wxString UTF-8 round-trip" << std::endl;
            failures++;
        }
    }

    // ---- Test 4: wxVersion string check ----
    {
        wxString version(wxVERSION_STRING);
        if (version != "wxWidgets 3.2.6") {
            std::cerr << "FAIL: wxVersion (expected 'wxWidgets 3.2.6', got '"
                      << version << "')" << std::endl;
            failures++;
        }
    }

    // ---- Test 5: wxMutex basic API ----
    {
        wxMutex mutex;

        wxMutexError err = mutex.Lock();
        if (err != wxMUTEX_NO_ERROR) {
            std::cerr << "FAIL: wxMutex.Lock()" << std::endl;
            failures++;
        }

        err = mutex.Unlock();
        if (err != wxMUTEX_NO_ERROR) {
            std::cerr << "FAIL: wxMutex.Unlock()" << std::endl;
            failures++;
        }

        err = mutex.TryLock();
        if (err != wxMUTEX_NO_ERROR) {
            std::cerr << "FAIL: wxMutex.TryLock()" << std::endl;
            failures++;
        }
        mutex.Unlock();  // clean up after TryLock
    }

    // ---- Summary ----
    if (failures == 0) {
        std::cout << "wxWidgets 3.2.6 smoke test: ALL PASSED" << std::endl;
        return 0;
    } else {
        std::cerr << "wxWidgets 3.2.6 smoke test: " << failures << " FAILURES" << std::endl;
        return 1;
    }
}
