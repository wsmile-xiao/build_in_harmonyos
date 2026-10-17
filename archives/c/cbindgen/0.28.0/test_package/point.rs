#[repr(C)]
pub struct CbindgenPoint {
    pub x: f64,
    pub y: f64,
}

#[no_mangle]
pub extern "C" fn cbindgen_norm_sq(point: CbindgenPoint) -> f64 {
    point.x * point.x + point.y * point.y
}
