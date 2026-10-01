# ktextwidgets 6.18.0 notes

## Scope

This package provides `KF6::TextWidgets`, required by `akonadi-contacts` and the restored TextAutoCorrection part of `ktextaddons`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `WITH_TEXT_TO_SPEECH=OFF` avoids the optional Qt TextToSpeech module.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt Designer plugin generation.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 5/5 passed.
- test_package CTest: 1/1 passed.
- Direct test executable:
  `PASS: KTextWidgets KReplace produced Akonadi libraries consume text widgets`.
- Full package reference:
  `ktextwidgets/6.18.0#fa14ea41740885b92c477b8cf03f9e0e:72aa787624c810c3b5de0def8527a7e47fb3d906#c7df7010cb10ac6732d8709ae3200fb1`.
