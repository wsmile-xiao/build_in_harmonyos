# Geogram 1.10.1 adaptation notes

- The named GitHub release asset is required because the automatically
  generated source archive omits Geogram submodules/vendor content.
- The package uses Geogram's library-only mode with graphics, TBB, and legacy
  numerical plugins, and Exploragram disabled. The remaining third-party sources are vendored
  in the release asset, so W0 has no Conan dependency graph.
- The upstream platform selector has no OHOS entry. The adaptation adds a
  task-local `OHOS-clang` configuration that reuses Linux clang capability
  flags without the x86-only `-m64` option.
