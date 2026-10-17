# cbmconvert

cbmconvert creates, extracts and converts 8-bit Commodore binary archives:
1541/1571/1581 disk images (D64/D71/D81), Lynx archives, Commodore C2N tape
files, with zip round-trips through the bundled `zip2disk`/`disk2zip` tools.
The `2.1.6` recipe builds the upstream CMake project natively on OHOS with
clang (presented as generic Linux/aarch64) and packages the three
executables; it declares no Conan package dependencies.

The upstream 6-test CTest suite runs inside the recipe build; the consumer
test exercises a real D64 image creation and Lynx back-conversion.
