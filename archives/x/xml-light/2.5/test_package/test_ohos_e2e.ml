(* xml-light test_package — HarmonyOS PC 端到端消费者用例（rule12）
 *
 * 与 test_xml_light.ml（纯内存断言）不同，本用例走完整消费者流程：
 *   1. 以 OHOS worker 上的真实文件系统为数据源（写出 HarmonyOS 风格的
 *      module 配置 XML 与对应 DTD 文件；内容为紧凑格式，不依赖解析器
 *      对空白 PCData 的处理策略）
 *   2. Dtd.parse_file + Dtd.check 从文件解析并校验 DTD（库的真实 I/O
 *      消费路径，与上游 tests/check_dtd.ml 相同的用法）
 *   3. Xml.parse_file 解析整档 + Dtd.prove 完成针对 DTD 的证明
 *      （XmlParser 对象 API 亦以 SString/SFile 双源各跑一遍）
 *   4. 断言解析结果结构 + 负向控制（缺必填属性的配置必须被 DTD 校验
 *      拒绝）+ 清理临时文件
 * 原生二进制在 HarmonyOS PC worker（aarch64-linux-ohos 用户态）上执行，
 * 验证的是「OHOS 环境下该库可被消费者端到端使用」这一平台特性。
 *)

let tmp = try Sys.getenv "TMPDIR" with Not_found -> "/tmp"
let xml_path = Filename.concat tmp "xml_light_ohos_e2e.xml"
let bad_path = Filename.concat tmp "xml_light_ohos_e2e_bad.xml"
let dtd_path = Filename.concat tmp "xml_light_ohos_e2e.dtd"

let is_element = function Xml.Element _ -> true | _ -> false

let () =
  (* 1) 写出 HarmonyOS 风格 module 配置（真实文件 I/O；紧凑格式）
        deviceTypes 是 OHOS module.json5 的标志性字段名 *)
  let oc = open_out xml_path in
  output_string oc "<module-config bundle=\"com.example.xml-light\" \
target=\"default\"><deviceTypes>tablet</deviceTypes>\
<deviceTypes>2in1</deviceTypes></module-config>\n";
  close_out oc;

  (* 缺少必填 bundle 属性的坏配置（负向控制数据） *)
  let oc = open_out bad_path in
  output_string oc "<module-config><deviceTypes>tablet</deviceTypes>\
</module-config>\n";
  close_out oc;

  (* 2) DTD 文件：bundle 必填、target 可选、deviceTypes 可重复 *)
  let oc = open_out dtd_path in
  output_string oc "<!ELEMENT module-config (deviceTypes*)>\n";
  output_string oc "<!ATTLIST module-config bundle NMTOKEN #REQUIRED>\n";
  output_string oc "<!ATTLIST module-config target NMTOKEN #IMPLIED>\n";
  output_string oc "<!ELEMENT deviceTypes (#PCDATA)>\n";
  close_out oc;

  (* 3) Dtd.parse_file + check（文件 I/O 路径）；Xml.parse_file 解析整档；
        Dtd.prove 完成 DTD 证明（上游 check_dtd.ml 同款流程） *)
  let checked = Dtd.check (Dtd.parse_file dtd_path) in
  let x = Xml.parse_file xml_path in
  let x = Dtd.prove checked "module-config" x in
  assert (Xml.tag x = "module-config");
  assert (Xml.attrib x "bundle" = "com.example.xml-light");
  assert (Xml.attrib x "target" = "default");
  let elems = List.filter is_element (Xml.children x) in
  assert (List.length elems = 2);
  (match elems with
   | first :: second :: _ ->
     assert (Xml.tag first = "deviceTypes");
     assert (Xml.tag second = "deviceTypes");
     (match Xml.children first with
      | [Xml.PCData t] -> assert (t = "tablet")
      | _ -> assert false)
   | _ -> assert false);
  Printf.printf "ohos module config parsed + dtd-proved ok: bundle=%s\n"
    (Xml.attrib x "bundle");

  (* 4) XmlParser 对象 API（make/parse，SString 与 SFile 双数据源） *)
  let p = XmlParser.make () in
  let y = XmlParser.parse p (XmlParser.SString "<a x=\"1\"><b/></a>") in
  assert (Xml.tag y = "a");
  assert (Xml.attrib y "x" = "1");
  assert (List.length (Xml.children y) = 1);
  let z = XmlParser.parse p (XmlParser.SFile xml_path) in
  assert (Xml.tag z = "module-config");
  assert (Xml.attrib z "bundle" = "com.example.xml-light");
  Printf.printf "xmlparser object api ok: SString + SFile\n";

  (* 5) 负向控制：缺必填 bundle 的配置必须被 Dtd.prove 拒绝
        （Dtd 异常为 Xml_light_errors 中定义的别名，任何 DTD 错误类别
        都算作正确拒绝） *)
  (try
     let bad = Xml.parse_file bad_path in
     let _ = Dtd.prove checked "module-config" bad in
     assert false  (* expected a DTD rejection *)
   with
   | Dtd.Prove_error _ ->
     Printf.printf "negative control ok: DTD proved rejection raised\n"
   | Dtd.Check_error _ ->
     Printf.printf "negative control ok: DTD check rejection raised\n"
   | Dtd.Parse_error _ ->
     Printf.printf "negative control ok: DTD parse rejection raised\n");

  (* 清理 + 成功输出 *)
  Sys.remove xml_path;
  Sys.remove bad_path;
  Sys.remove dtd_path;
  Printf.printf "ohos e2e: module config validated against DTD on disk\n";
  Printf.printf "ALL OHOS E2E PASSED\n"
