// Test: directx-headers 1.619.1
// Verifies that the DirectX headers are usable and the property format table library links correctly.

#include <wsl/winadapter.h>
#include <directx/d3d12.h>
#include <directx/d3dx12.h>
#include <directx/dxgiformat.h>
#include <directx/d3dx12_property_format_table.h>
#include "dxguids/dxguids.h"

int main()
{
    // Check that D3D12 types are usable from headers
    D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_11_0;
    if (featureLevel != D3D_FEATURE_LEVEL_11_0) {
        return 1;
    }

    // Check UUID linkage (from DirectX-Guids library)
    auto uuid_i_unknown = IID_IUnknown;
    (void)uuid_i_unknown;  // Verify symbol is available at link time

    // Check property format table (from DirectX-Headers library)
    // GetNumFormats() is a static method that exercises the compiled library code
    UINT numFormats = D3D12_PROPERTY_LAYOUT_FORMAT_TABLE::GetNumFormats();
    if (numFormats == 0) {
        return 1;
    }

    return 0;
}
