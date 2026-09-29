#!/bin/sh
# cairo2 test_package smoke test (L0c source)
# 编译一个小 OCaml 程序与被测包 cairo.cmxa + libcairo_stubs.a 实际链接，
# 运行绘制冒烟测试：image surface 绘制 + PNG 写出 + 读回。
# 依赖 conanfile.py test() 注入的环境: PKG_LIB / LD_LIBRARY_PATH / OCAMLLIB
set -e

cat > test_cairo2.ml <<'EOF'
let () =
  let surf = Cairo.Image.create Cairo.Image.ARGB32 ~w:64 ~h:64 in
  let cr = Cairo.create surf in
  Cairo.set_source_rgb cr 1.0 0.0 0.0;
  Cairo.move_to cr 10. 10.;
  Cairo.line_to cr 50. 50.;
  Cairo.stroke cr;
  let png = Filename.concat (Filename.get_temp_dir_name ()) "cairo2-test.png" in
  Cairo.PNG.write surf png;
  assert (Sys.file_exists png);
  let surf2 = Cairo.PNG.create png in
  Cairo.Surface.finish surf2;
  Sys.remove png;
  Format.printf "cairo2 smoke OK: surface drawn, PNG written and read back@."
EOF

ocamlopt -I "$PKG_LIB" cairo.cmxa test_cairo2.ml -o test_cairo2
./test_cairo2
