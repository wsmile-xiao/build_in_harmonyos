# Packaging

PostgreSQL extension hypopg is packaged via Conan (conan create).
The Conan package contains:
- lib/hypopg.so - PostgreSQL extension shared library
- res/hypopg.control - Extension control file
- res/hypopg--*.sql - SQL migration files

No manual packaging required - Conan handles package creation.
