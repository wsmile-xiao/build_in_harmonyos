/*
 * MIT License
 *
 * Copyright (c) 2016 Michael Angstadt
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

import com.github.mangstadt.vinnie.io.VObjectReader;
import com.github.mangstadt.vinnie.io.VObjectWriter;
import com.github.mangstadt.vinnie.io.SyntaxRules;
import com.github.mangstadt.vinnie.io.VObjectDataAdapter;
import com.github.mangstadt.vinnie.io.Context;
import com.github.mangstadt.vinnie.VObjectProperty;
import com.github.mangstadt.vinnie.SyntaxStyle;

import java.io.StringReader;
import java.io.StringWriter;
import java.util.List;

/**
 * TestVinnie — vinnie 2.0.2 API integration test
 *
 * Uses VObjectReader to parse vCard data and VObjectWriter to write it back,
 * validating that the core read/write APIs work correctly on HarmonyOS PC.
 */
public class TestVinnie {
    public static void main(String[] args) throws Exception {
        // Sample vCard data
        String vcard = "BEGIN:VCARD\n" +
                       "VERSION:3.0\n" +
                       "FN:John Doe\n" +
                       "EMAIL:john@example.com\n" +
                       "END:VCARD";

        // --- Test 1: Parse vCard and verify property values ---
        final StringBuilder parsedName = new StringBuilder();
        final StringBuilder parsedEmail = new StringBuilder();
        final int[] propertyCount = {0};

        VObjectReader reader = new VObjectReader(
            new StringReader(vcard),
            SyntaxRules.vcard()
        );
        reader.parse(new VObjectDataAdapter() {
            @Override
            public void onProperty(VObjectProperty property, Context context) {
                propertyCount[0]++;
                if ("FN".equals(property.getName())) {
                    parsedName.append(property.getValue());
                } else if ("EMAIL".equals(property.getName())) {
                    parsedEmail.append(property.getValue());
                }
            }
        });
        reader.close();

        if (!parsedName.toString().equals("John Doe")) {
            System.err.println("FAIL: Expected FN='John Doe', got '" + parsedName + "'");
            System.exit(1);
        }
        if (!parsedEmail.toString().equals("john@example.com")) {
            System.err.println("FAIL: Expected EMAIL='john@example.com', got '" + parsedEmail + "'");
            System.exit(1);
        }
        if (propertyCount[0] < 2) {
            // VObjectReader consumes the VERSION line internally to select the
            // vCard syntax rules, so it is not delivered to onProperty. The
            // delivered properties are the data lines (FN, EMAIL, ...).
            System.err.println("FAIL: Expected at least 2 properties delivered to onProperty, got " + propertyCount[0]);
            System.exit(1);
        }

        // --- Test 2: Write vCard and verify output format ---
        StringWriter writer = new StringWriter();
        VObjectWriter vcardWriter = new VObjectWriter(writer, SyntaxStyle.NEW);
        vcardWriter.writeBeginComponent("VCARD");
        vcardWriter.writeVersion("3.0");
        vcardWriter.writeProperty("FN", "Jane Smith");
        vcardWriter.writeProperty("TEL", "555-1234");
        vcardWriter.writeEndComponent("VCARD");
        vcardWriter.close();

        String output = writer.toString();
        if (!output.contains("BEGIN:VCARD")) {
            System.err.println("FAIL: Output missing 'BEGIN:VCARD'");
            System.exit(1);
        }
        if (!output.contains("FN:Jane Smith")) {
            System.err.println("FAIL: Output missing 'FN:Jane Smith'");
            System.exit(1);
        }
        if (!output.contains("END:VCARD")) {
            System.err.println("FAIL: Output missing 'END:VCARD'");
            System.exit(1);
        }

        // --- Test 3: Round-trip test (parse what we wrote) ---
        VObjectReader roundTripReader = new VObjectReader(
            new StringReader(output),
            SyntaxRules.vcard()
        );
        final StringBuilder rtName = new StringBuilder();
        roundTripReader.parse(new VObjectDataAdapter() {
            @Override
            public void onProperty(VObjectProperty property, Context context) {
                if ("FN".equals(property.getName())) {
                    rtName.append(property.getValue());
                }
            }
        });
        roundTripReader.close();

        if (!rtName.toString().equals("Jane Smith")) {
            System.err.println("FAIL: Round-trip FN mismatch, got '" + rtName + "'");
            System.exit(1);
        }

        System.out.println("PASS: vinnie 2.0.2 API test - VObjectReader/VObjectWriter work correctly");
    }
}
