# ceph 20.2.2

- Packages the standalone CRUSH data-placement core as a static library.
- Excludes Linux-only Ceph daemons, RADOS clients, and `crushtool`.
- Uses portable fixed-width integer aliases instead of Linux UAPI headers.
- Compiles four adapted upstream CRUSH scenarios and one installed-package
  consumer test.
- Local native tests passed 4/4 upstream and 1/1 consumer checks.
