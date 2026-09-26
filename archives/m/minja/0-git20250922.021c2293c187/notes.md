# minja 0-git20250922.021c2293c187

This recipe packages the header-only C++17 library from upstream commit
`021c2293c187789ef13d56c6cfd89c9b134fd80f` and exposes the `minja::minja`
CMake target. It uses the existing `nlohmann_json/3.12.0` package.

The HarmonyOS aarch64 `conan create` completed with exit code 0. The self-contained
upstream parser, chat-template, and polyfill GoogleTest suites passed 10/10 cases
(1 syntax, 1 chat-template, 8 non-model polyfill cases). A consumer executable
compiled and passed 1/1 case for raw rendering and chat-template prompt generation.

The full model-template matrix and model-specific `ToolTest` cases fetch mutable
Hugging Face `tokenizer_config.json` and template files at configure/runtime. Those
external-data cases are excluded by the patch and are not counted as passed. No
upstream test source files were modified; the patch changes dependency wiring and
test registration only.
