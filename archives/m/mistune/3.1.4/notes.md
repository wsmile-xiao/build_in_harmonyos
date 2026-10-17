# mistune 3.1.4 HarmonyOS PC package

- Upstream: `lepture/mistune`, tag `v3.1.4` (`b6d83e82cfa781285d77ab4f719b18b9559603b5`)
- Source: PyPI sdist, SHA256 pinned in `conandata.yml`
- Package type: pure-Python Conan `python-require`
- Runtime dependencies: none for the target Conan Python 3.14; upstream declares `typing-extensions` only for Python <3.11
- Build: copies `src/mistune` to a private stage and runs the official `unittest` suite from the sdist
- Upstream test modules: seven; 949 tests collected and run by `unittest discover`
- Consumer validation: imports the Conan package and checks version, rendering, plugins, AST output, HTML escaping, and harmful-link handling
- No executable is installed, so this package does not need a `commands.json` declaration.
