// Consumer test for the packaged `rutabaga` (crates.io `rutabaga_gfx`) OHOS
// library.  It links the packaged `librutabaga_gfx.rlib` and exercises the real
// public API, plus the HarmonyOS-specific runtime path (writable TMPDIR and the
// aarch64-linux-ohos target).
extern crate rutabaga_gfx;

use std::fmt::Write;

use rutabaga_gfx::{
    DrmFormat, RutabagaBuilder, RutabagaComponentType, RutabagaHandler,
};

fn main() {
    let mut checks = 0usize;

    // CHECK 1 — public format API (DrmFormat::new + Debug impl).
    let f = DrmFormat::new(b'X', b'R', b'2', b'4');
    let mut buf = String::new();
    write!(&mut buf, "{:?}", f).unwrap();
    assert_eq!(buf, "fourcc(XR24)");
    println!("CHECK-OK: DrmFormat::new/Debug -> {}", buf);
    checks += 1;

    // CHECK 2 — VGI core builder with the 2D component.
    let mut rutabaga = RutabagaBuilder::new(0, RutabagaHandler::new(|_| {}))
        .set_default_component(RutabagaComponentType::Rutabaga2D)
        .build()
        .expect("RutabagaBuilder::build failed");
    println!("CHECK-OK: RutabagaBuilder::build (Rutabaga2D)");
    checks += 1;

    // CHECK 3 (OHOS-specific) — target must be aarch64-unknown-linux-ohos.
    assert_eq!(std::env::consts::ARCH, "aarch64");
    #[cfg(target_env = "ohos")]
    {
        println!("CHECK-OK(OHOS): aarch64-unknown-linux-ohos (target_env=ohos)");
        checks += 1;
    }
    #[cfg(not(target_env = "ohos"))]
    {
        panic!("test_package must be built for aarch64-unknown-linux-ohos");
    }

    // CHECK 4 (OHOS-specific) — snapshot/restore round-trip under the device
    // writable TMPDIR (HarmonyOS /tmp is read-only, so TMPDIR is redirected).
    let dir = std::env::temp_dir().join("rutabaga_ohos_consumer_snapshot");
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    rutabaga.snapshot(dir.as_path()).expect("snapshot failed");
    rutabaga.restore(dir.as_path()).expect("restore failed");
    std::fs::remove_dir_all(&dir).unwrap();
    println!("CHECK-OK(OHOS): TMPDIR snapshot/restore -> {}", dir.display());
    checks += 1;

    println!("CONSUMER-PASS: {} checks", checks);
}
