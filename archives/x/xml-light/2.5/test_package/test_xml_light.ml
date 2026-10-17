(* xml-light test_package — consumer test (R34: really uses the package)
 *
 * Exercises the packaged xml-light library's public modules (the library
 * stanza has `wrapped false`, so modules keep top-level names):
 *   Xml        — parse_string / tag / attrib / children / to_string
 *                round-trip
 *   Dtd        — parse_string / check / prove, positive and negative
 *                controls
 * plus a malformed-XML negative control.
 *
 * Exception note (verified against the 2.5 sources): syntax errors escape
 * Xml.parse_string as the internal Xml_light_errors.Xml_error (Xml.Error
 * is not an alias of it), so the negative control catches both.
 *
 * The document is compact (no inter-element whitespace) so the assertions
 * hold regardless of the parser's blank-PCDATA policy.
 *
 * Compiled against the conan package (explicit cma/cmxa linkage — the
 * registry OCaml 4.14.1 has no findlib) both as bytecode (compile-only)
 * and native; the native binary must run and print ALL TESTS PASSED.
 *)

let doc =
  "<config version=\"1.0\"><item id=\"a1\" flag=\"on\">text</item>\
<item id=\"a2\">more</item></config>"

let dtd_src =
  "<!ELEMENT config (item*)>\n\
<!ATTLIST config version CDATA #REQUIRED>\n\
<!ELEMENT item (#PCDATA)>\n\
<!ATTLIST item id NMTOKEN #REQUIRED>\n\
<!ATTLIST item flag NMTOKEN #IMPLIED>\n"

let () =
  (* 1. Xml.parse_string: structure, attributes, children *)
  let x = Xml.parse_string doc in
  assert (Xml.tag x = "config");
  assert (Xml.attrib x "version" = "1.0");
  let children = Xml.children x in
  assert (List.length children = 2);
  (match children with
   | first :: second :: _ ->
     assert (Xml.tag first = "item");
     assert (Xml.attrib first "id" = "a1");
     assert (Xml.attrib first "flag" = "on");
     assert (Xml.attrib second "id" = "a2")
   | _ -> assert false);
  Printf.printf "parse_string ok: tag=%s children=%d id=%s\n"
    (Xml.tag x) (List.length children) (Xml.attrib (List.hd children) "id");

  (* 2. PCDATA content access *)
  (match Xml.children (List.hd children) with
   | [Xml.PCData text] -> assert (text = "text")
   | _ -> assert false);
  Printf.printf "pcdata ok: text\n";

  (* 3. to_string round-trip: printed output must reparse to same shape *)
  let printed = Xml.to_string x in
  let x2 = Xml.parse_string printed in
  assert (Xml.tag x2 = "config");
  assert (List.length (Xml.children x2) = 2);
  assert (Xml.attrib (List.hd (Xml.children x2)) "id" = "a1");
  Printf.printf "to_string round-trip ok (%d chars)\n" (String.length printed);

  (* 4. negative control: malformed XML must be rejected by the parser
        (syntax errors escape as Xml_light_errors.Xml_error; Xml.Error is
        also accepted for other error paths) *)
  (try
     let _ = Xml.parse_string "<config><item></wrong>" in
     assert false  (* expected an error *)
   with
   | Xml_light_errors.Xml_error _ ->
     Printf.printf "negative control ok: Xml_light_errors.Xml_error raised\n"
   | Xml.Error _ ->
     Printf.printf "negative control ok: Xml.Error raised\n");

  (* 5. Dtd.parse_string + check + prove (positive) *)
  let checked = Dtd.check (Dtd.parse_string dtd_src) in
  let proven = Dtd.prove checked "config" x in
  assert (Xml.tag proven = "config");
  Printf.printf "dtd parse/check/prove ok: root=%s\n" (Xml.tag proven);

  (* 6. Dtd negative control: wrong root name must be rejected by prove
        (an undeclared root raises Check_error ElementNotDeclared from
        start_prove; prove-stage violations raise Prove_error — both count
        as a correct rejection) *)
  (try
     let _ = Dtd.prove checked "notconfig" x in
     assert false  (* expected an error *)
   with
   | Dtd.Prove_error _ ->
     Printf.printf "dtd negative control ok: Dtd.Prove_error raised\n"
   | Dtd.Check_error _ ->
     Printf.printf "dtd negative control ok: root-not-declared rejected\n");

  Printf.printf "ALL TESTS PASSED\n"
