#include <wx/init.h>
#include <wx/memory.h>
#include <wx/string.h>
#include <wx/tokenzr.h>
#include <wx/uri.h>
#include <wx/version.h>

#include <iostream>

int main()
{
    wxInitializer initializer;
    if ( !initializer.IsOk() )
    {
        std::cerr << "wxWidgets initialization failed\n";
        return 1;
    }

    const wxString text = wxString::FromUTF8("OpenHarmony PC");
    if ( text.Upper() != "OPENHARMONY PC" )
        return 2;

    wxStringTokenizer tokens(text, " ");
    if ( tokens.CountTokens() != 2 || tokens.GetNextToken() != "OpenHarmony" )
        return 3;

    const wxURI uri("https://www.wxwidgets.org/docs/");
    if ( uri.GetScheme() != "https" || uri.GetServer() != "www.wxwidgets.org" )
        return 4;

    wxMemoryBuffer buffer;
    buffer.AppendData("wx", 2);
    if ( buffer.GetDataLen() != 2 )
        return 5;

    if ( wxMAJOR_VERSION != 3 || wxMINOR_VERSION != 3 ||
         wxRELEASE_NUMBER != 3 )
        return 6;

    std::cout << "wxWidgets 3.3.3 consumer test passed\n";
    return 0;
}
