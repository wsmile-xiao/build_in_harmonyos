/**
 * TestWeupnp — weupnp 0.1.4 consumer / functional test suite.
 *
 * Runs against the *packaged* JAR (passed with -Dweupnp.jar=<path>), so every
 * case exercises the real artifact exactly as a consumer would.
 *
 * Coverage:
 *   - PortMappingEntry          : value object contract
 *   - NameValueHandler          : SAX name/value parsing (real XMLReader)
 *   - GatewayDeviceHandler      : IGD device-description parsing + service state machine
 *   - GatewayDevice             : SSDP/SOAP protocol layer against a local mock IGD
 *                                 (SOAP envelope, SOAPAction header, all 6 UPnP actions,
 *                                  UPnP error path, device description over HTTP)
 *   - GatewayDiscover           : constructors, timeout API, live SSDP discovery
 *   - Main                      : upstream demo entry point (the only runnable upstream sample)
 *   - OHOS_*                    : OHOS-platform specific cases (see below)
 *
 * OHOS-specific cases (>= 1 required):
 *   OHOS_01  platform/JVM identity on OHOS (harmonyos kernel + BiSheng JDK 17)
 *   OHOS_02  SSDP multicast transport on the OHOS network stack
 *   OHOS_03  packaged JAR bytecode/OSGi headers are loadable by the OHOS JVM
 *
 * Plain Java only — no JUnit, so the suite has no external dependency.
 */
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.StringReader;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.jar.Manifest;

import org.bitlet.weupnp.GatewayDevice;
import org.bitlet.weupnp.GatewayDeviceHandler;
import org.bitlet.weupnp.GatewayDiscover;
import org.bitlet.weupnp.Main;
import org.bitlet.weupnp.NameValueHandler;
import org.bitlet.weupnp.PortMappingEntry;
import org.xml.sax.InputSource;
import org.xml.sax.XMLReader;
import org.xml.sax.helpers.XMLReaderFactory;

@SuppressWarnings("deprecation")
public class TestWeupnp {

    private static final String WAN_SERVICE =
            "urn:schemas-upnp-org:service:WANIPConnection:1";
    private static final String CIF_SERVICE =
            "urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1";

    // ── tiny assertion harness ────────────────────────────────────────────────

    static int total = 0;
    static int passed = 0;
    static int failed = 0;
    static int skipped = 0;
    static final List<String> failedNames = new ArrayList<String>();
    static final List<String> skippedNames = new ArrayList<String>();

    interface Case {
        void run() throws Throwable;
    }

    static class Skip extends RuntimeException {
        Skip(String message) {
            super(message);
        }
    }

    static void test(String name, Case body) {
        total++;
        try {
            body.run();
            passed++;
            System.out.println("PASS   " + name);
        } catch (Skip skip) {
            skipped++;
            skippedNames.add(name);
            System.out.println("SKIP   " + name + " :: " + skip.getMessage());
        } catch (Throwable error) {
            failed++;
            failedNames.add(name);
            System.out.println("FAIL   " + name + " :: " + error);
            error.printStackTrace(System.out);
        }
    }

    static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    static void eq(Object actual, Object expected, String message) {
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new AssertionError(message + " [expected=" + expected
                    + ", actual=" + actual + "]");
        }
    }

    static void contains(String haystack, String needle, String message) {
        check(haystack != null && haystack.contains(needle),
                message + " [missing '" + needle + "']");
    }

    // ── local mock IGD (HTTP/SOAP endpoint) ───────────────────────────────────

    static class MockIgd {
        final HttpServer server;
        final Map<String, String> canned = new HashMap<String, String>();
        volatile String lastSoapAction = "";
        volatile String lastContentType = "";
        volatile String lastBody = "";
        volatile boolean errorMode = false;
        volatile String descXml = "";

        MockIgd() throws IOException {
            server = HttpServer.create(
                    new InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0), 0);
            server.createContext("/control", new HttpHandler() {
                public void handle(HttpExchange exchange) throws IOException {
                    lastSoapAction =
                            exchange.getRequestHeaders().getFirst("SOAPAction");
                    lastContentType =
                            exchange.getRequestHeaders().getFirst("Content-Type");
                    lastBody = readFully(exchange.getRequestBody());
                    if (errorMode) {
                        send(exchange, 500, soapFault("606", "Action not authorized"));
                        return;
                    }
                    String action = actionOf(lastBody);
                    String response = canned.get(action);
                    if (response == null) {
                        send(exchange, 500, soapFault("401", "Invalid Action"));
                        return;
                    }
                    send(exchange, 200, response);
                }
            });
            server.createContext("/desc.xml", new HttpHandler() {
                public void handle(HttpExchange exchange) throws IOException {
                    send(exchange, 200, descXml);
                }
            });
            server.setExecutor(null);
            server.start();
        }

        String base() {
            return "http://127.0.0.1:" + server.getAddress().getPort();
        }

        void stop() {
            server.stop(0);
        }
    }

    static String readFully(InputStream stream) throws IOException {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        while ((read = stream.read(chunk)) > 0) {
            buffer.write(chunk, 0, read);
        }
        stream.close();
        return new String(buffer.toByteArray(), "UTF-8");
    }

    static void send(HttpExchange exchange, int status, String body) throws IOException {
        byte[] payload = body.getBytes("UTF-8");
        exchange.getResponseHeaders().set("Content-Type", "text/xml");
        exchange.sendResponseHeaders(status, payload.length);
        OutputStream out = exchange.getResponseBody();
        out.write(payload);
        out.close();
    }

    static String actionOf(String soapBody) {
        int marker = soapBody.indexOf("<m:");
        if (marker < 0) {
            return "";
        }
        int end = soapBody.indexOf(' ', marker);
        return end < 0 ? "" : soapBody.substring(marker + 3, end);
    }

    static String soapResponse(String action, String... pairs) {
        StringBuilder xml = new StringBuilder();
        xml.append("<?xml version=\"1.0\"?>")
           .append("<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\"")
           .append(" s:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\">")
           .append("<s:Body><u:").append(action).append("Response xmlns:u=\"")
           .append(WAN_SERVICE).append("\">");
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            xml.append('<').append(pairs[i]).append('>')
               .append(pairs[i + 1])
               .append("</").append(pairs[i]).append('>');
        }
        xml.append("</u:").append(action).append("Response></s:Body></s:Envelope>");
        return xml.toString();
    }

    static String soapFault(String code, String description) {
        return "<?xml version=\"1.0\"?>"
                + "<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\""
                + " s:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\">"
                + "<s:Body><s:Fault><faultcode>s:Client</faultcode>"
                + "<faultstring>UPnPError</faultstring>"
                + "<detail><UPnPError xmlns=\"urn:schemas-upnp-org:control-1-0\">"
                + "<errorCode>" + code + "</errorCode>"
                + "<errorDescription>" + description + "</errorDescription>"
                + "</UPnPError></detail></s:Fault></s:Body></s:Envelope>";
    }

    static String deviceDescription(int port) {
        return "<?xml version=\"1.0\"?>"
                + "<root xmlns=\"urn:schemas-upnp-org:device-1-0\">"
                + "<specVersion><major>1</major><minor>0</minor></specVersion>"
                + "<URLBase>http://127.0.0.1:" + port + "/</URLBase>"
                + "<device>"
                + "<deviceType>urn:schemas-upnp-org:device:InternetGatewayDevice:1</deviceType>"
                + "<friendlyName>Mock IGD (OHOS)</friendlyName>"
                + "<manufacturer>OpenHarmony PC Developer</manufacturer>"
                + "<manufacturerURL>https://example.invalid/</manufacturerURL>"
                + "<modelDescription>Mock UPnP IGD for the weupnp test_package</modelDescription>"
                + "<modelName>MockRouter</modelName>"
                + "<modelNumber>1.0</modelNumber>"
                + "<presentationURL>/index.html</presentationURL>"
                + "<serviceList>"
                + "  <service>"
                + "    <serviceType>" + CIF_SERVICE + "</serviceType>"
                + "    <controlURL>/cif/control</controlURL>"
                + "    <eventSubURL>/cif/event</eventSubURL>"
                + "    <SCPDURL>/cif/scpd.xml</SCPDURL>"
                + "  </service>"
                + "  <service>"
                + "    <serviceType>" + WAN_SERVICE + "</serviceType>"
                + "    <controlURL>/control</controlURL>"
                + "    <eventSubURL>/event</eventSubURL>"
                + "    <SCPDURL>/scpd.xml</SCPDURL>"
                + "  </service>"
                + "</serviceList>"
                + "</device></root>";
    }

    static GatewayDevice deviceFor(MockIgd igd) throws Exception {
        GatewayDevice device = new GatewayDevice();
        device.setServiceType(WAN_SERVICE);
        device.setControlURL(igd.base() + "/control");
        device.setLocalAddress(InetAddress.getByName("127.0.0.1"));
        return device;
    }

    static XMLReader xmlReader() throws Exception {
        return XMLReaderFactory.createXMLReader();
    }

    // ── cases ─────────────────────────────────────────────────────────────────

    static void runCases() throws Exception {
        final MockIgd igd = new MockIgd();
        igd.descXml = deviceDescription(igd.server.getAddress().getPort());
        try {
            runCases(igd);
        } finally {
            igd.stop();
        }
    }

    static void runCases(final MockIgd igd) throws Exception {

        // ── value object ──
        test("PortMappingEntry_setters_getters", () -> {
            PortMappingEntry entry = new PortMappingEntry();
            entry.setExternalPort(6991);
            entry.setInternalPort(6990);
            entry.setRemoteHost("203.0.113.9");
            entry.setInternalClient("192.0.2.10");
            entry.setProtocol("TCP");
            entry.setEnabled("1");
            entry.setPortMappingDescription("ohos-weupnp-test");
            eq(entry.getExternalPort(), 6991, "externalPort");
            eq(entry.getInternalPort(), 6990, "internalPort");
            eq(entry.getRemoteHost(), "203.0.113.9", "remoteHost");
            eq(entry.getInternalClient(), "192.0.2.10", "internalClient");
            eq(entry.getProtocol(), "TCP", "protocol");
            eq(entry.getEnabled(), "1", "enabled");
            eq(entry.getPortMappingDescription(), "ohos-weupnp-test", "description");
        });

        // ── SAX name/value layer ──
        test("NameValueHandler_parses_name_value_xml", () -> {
            Map<String, String> values = new HashMap<String, String>();
            XMLReader parser = xmlReader();
            parser.setContentHandler(new NameValueHandler(values));
            parser.parse(new InputSource(new StringReader(
                    "<?xml version=\"1.0\"?><root>"
                            + "<NewExternalIPAddress>203.0.113.7</NewExternalIPAddress>"
                            + "<NewPortMappingDescription>ohos-test</NewPortMappingDescription>"
                            + "</root>")));
            eq(values.get("NewExternalIPAddress"), "203.0.113.7", "external IP parsed");
            eq(values.get("NewPortMappingDescription"), "ohos-test", "description parsed");
        });

        test("NameValueHandler_concatenates_repeated_names", () -> {
            Map<String, String> values = new HashMap<String, String>();
            XMLReader parser = xmlReader();
            parser.setContentHandler(new NameValueHandler(values));
            parser.parse(new InputSource(new StringReader(
                    "<?xml version=\"1.0\"?><root><a>x</a><a>y</a><a>z</a></root>")));
            eq(values.get("a"), "xyz", "repeated elements are concatenated");
        });

        // ── device description parsing ──
        test("GatewayDeviceHandler_parses_igd_description", () -> {
            GatewayDevice device = new GatewayDevice();
            XMLReader parser = xmlReader();
            parser.setContentHandler(new GatewayDeviceHandler(device));
            parser.parse(new InputSource(new StringReader(deviceDescription(6991))));
            eq(device.getFriendlyName(), "Mock IGD (OHOS)", "friendlyName");
            eq(device.getManufacturer(), "OpenHarmony PC Developer", "manufacturer");
            eq(device.getModelName(), "MockRouter", "modelName");
            eq(device.getModelNumber(), "1.0", "modelNumber");
            eq(device.getModelDescription(),
                    "Mock UPnP IGD for the weupnp test_package", "modelDescription");
            eq(device.getURLBase(), "http://127.0.0.1:6991/", "URLBase");
        });

        test("GatewayDeviceHandler_service_state_machine", () -> {
            GatewayDevice device = new GatewayDevice();
            XMLReader parser = xmlReader();
            parser.setContentHandler(new GatewayDeviceHandler(device));
            parser.parse(new InputSource(new StringReader(deviceDescription(6991))));
            // The state machine must keep the WANCommonInterfaceConfig service in the
            // *CIF slots and promote WANIPConnection into the primary slots.
            eq(device.getServiceTypeCIF(), CIF_SERVICE, "serviceTypeCIF");
            eq(device.getControlURLCIF(), "/cif/control", "controlURLCIF");
            eq(device.getEventSubURLCIF(), "/cif/event", "eventSubURLCIF");
            eq(device.getSCPDURLCIF(), "/cif/scpd.xml", "sCPDURLCIF");
            eq(device.getServiceType(), WAN_SERVICE, "serviceType");
            eq(device.getControlURL(), "/control", "controlURL");
            eq(device.getEventSubURL(), "/event", "eventSubURL");
            eq(device.getSCPDURL(), "/scpd.xml", "sCPDURL");
        });

        // ── SOAP protocol layer against the mock IGD ──
        igd.canned.put("GetGenericPortMappingEntry", soapResponse(
                "GetGenericPortMappingEntry",
                "NewRemoteHost", "", "NewExternalPort", "6991", "NewProtocol", "TCP",
                "NewInternalPort", "6990", "NewInternalClient", "192.0.2.10",
                "NewEnabled", "1", "NewPortMappingDescription", "ohos-mapping",
                "NewLeaseDuration", "0"));

        test("GatewayDevice_simpleUPnPcommand_soap_envelope", () -> {
            Map<String, String> args = new LinkedHashMap<String, String>();
            args.put("NewPortMappingIndex", "0");
            Map<String, String> result = GatewayDevice.simpleUPnPcommand(
                    igd.base() + "/control", WAN_SERVICE,
                    "GetGenericPortMappingEntry", args);
            eq(result.get("NewExternalPort"), "6991", "SOAP response parsed");
            eq(igd.lastSoapAction, "\"" + WAN_SERVICE + "#GetGenericPortMappingEntry\"",
                    "SOAPAction header");
            eq(igd.lastContentType, "text/xml", "Content-Type header");
            contains(igd.lastBody, "<m:GetGenericPortMappingEntry xmlns:m=\"" + WAN_SERVICE + "\">",
                    "SOAP action element carries the service namespace");
            contains(igd.lastBody, "<NewPortMappingIndex>0</NewPortMappingIndex>",
                    "SOAP argument marshalled");
            contains(igd.lastBody, "SOAP-ENV:Envelope", "SOAP envelope");
        });

        igd.canned.put("GetStatusInfo", soapResponse(
                "GetStatusInfo", "NewConnectionStatus", "Connected",
                "NewLastConnectionError", "ERROR_NONE", "NewUptime", "3600"));

        test("GatewayDevice_isConnected_true", () -> {
            check(deviceFor(igd).isConnected(), "isConnected() must be true for "
                    + "NewConnectionStatus=Connected");
        });

        igd.canned.put("GetExternalIPAddress", soapResponse(
                "GetExternalIPAddress", "NewExternalIPAddress", "203.0.113.7"));

        test("GatewayDevice_getExternalIPAddress", () -> {
            eq(deviceFor(igd).getExternalIPAddress(), "203.0.113.7", "external IP");
        });

        igd.canned.put("AddPortMapping", soapResponse("AddPortMapping"));

        test("GatewayDevice_addPortMapping_request_args", () -> {
            GatewayDevice device = deviceFor(igd);
            check(device.addPortMapping(6991, 6990, "192.0.2.10", "TCP", "ohos-mapping"),
                    "addPortMapping() must succeed on a non-error response");
            contains(igd.lastBody, "<NewRemoteHost></NewRemoteHost>", "NewRemoteHost");
            contains(igd.lastBody, "<NewExternalPort>6991</NewExternalPort>", "NewExternalPort");
            contains(igd.lastBody, "<NewProtocol>TCP</NewProtocol>", "NewProtocol");
            contains(igd.lastBody, "<NewInternalPort>6990</NewInternalPort>", "NewInternalPort");
            contains(igd.lastBody, "<NewInternalClient>192.0.2.10</NewInternalClient>",
                    "NewInternalClient");
            contains(igd.lastBody, "<NewEnabled>1</NewEnabled>", "NewEnabled");
            contains(igd.lastBody, "<NewPortMappingDescription>ohos-mapping</NewPortMappingDescription>",
                    "NewPortMappingDescription");
            contains(igd.lastBody, "<NewLeaseDuration>0</NewLeaseDuration>", "NewLeaseDuration");
        });

        igd.canned.put("GetSpecificPortMappingEntry", soapResponse(
                "GetSpecificPortMappingEntry",
                "NewInternalPort", "6990", "NewInternalClient", "192.0.2.10",
                "NewEnabled", "1", "NewPortMappingDescription", "ohos-specific",
                "NewRemoteHost", ""));

        test("GatewayDevice_getSpecificPortMappingEntry", () -> {
            PortMappingEntry entry = new PortMappingEntry();
            check(deviceFor(igd).getSpecificPortMappingEntry(6991, "TCP", entry),
                    "getSpecificPortMappingEntry() must return true");
            eq(entry.getExternalPort(), 6991, "externalPort");
            eq(entry.getInternalPort(), 6990, "internalPort");
            eq(entry.getProtocol(), "TCP", "protocol");
            eq(entry.getInternalClient(), "192.0.2.10", "internalClient");
            eq(entry.getEnabled(), "1", "enabled");
            eq(entry.getPortMappingDescription(), "ohos-specific", "description");
        });

        test("GatewayDevice_getGenericPortMappingEntry", () -> {
            PortMappingEntry entry = new PortMappingEntry();
            check(deviceFor(igd).getGenericPortMappingEntry(0, entry),
                    "getGenericPortMappingEntry() must return true");
            eq(entry.getExternalPort(), 6991, "externalPort");
            eq(entry.getInternalPort(), 6990, "internalPort");
            eq(entry.getProtocol(), "TCP", "protocol");
            eq(entry.getInternalClient(), "192.0.2.10", "internalClient");
            eq(entry.getPortMappingDescription(), "ohos-mapping", "description");
        });

        igd.canned.put("GetPortMappingNumberOfEntries", soapResponse(
                "GetPortMappingNumberOfEntries",
                "NewPortMappingNumberOfEntries", "3"));

        test("GatewayDevice_getPortMappingNumberOfEntries", () -> {
            eq(deviceFor(igd).getPortMappingNumberOfEntries(), Integer.valueOf(3),
                    "port mapping count");
        });

        igd.canned.put("DeletePortMapping", soapResponse("DeletePortMapping"));

        test("GatewayDevice_deletePortMapping", () -> {
            check(deviceFor(igd).deletePortMapping(6991, "TCP"),
                    "deletePortMapping() must return true");
            contains(igd.lastBody, "<m:DeletePortMapping xmlns:m=\"" + WAN_SERVICE + "\">",
                    "DeletePortMapping action");
        });

        test("GatewayDevice_upnp_error_response", () -> {
            igd.errorMode = true;
            try {
                Map<String, String> result = GatewayDevice.simpleUPnPcommand(
                        igd.base() + "/control", WAN_SERVICE, "GetGenericPortMappingEntry",
                        new LinkedHashMap<String, String>());
                eq(result.get("errorCode"), "606", "UPnP error code parsed from HTTP 500 body");
                PortMappingEntry entry = new PortMappingEntry();
                check(!deviceFor(igd).getGenericPortMappingEntry(0, entry),
                        "getGenericPortMappingEntry() must report false on a UPnP error");
            } finally {
                igd.errorMode = false;
            }
        });

        test("GatewayDevice_loadDescription_http", () -> {
            GatewayDevice device = new GatewayDevice();
            device.setLocation(igd.base() + "/desc.xml");
            device.loadDescription();
            eq(device.getFriendlyName(), "Mock IGD (OHOS)", "friendlyName from HTTP");
            eq(device.getModelName(), "MockRouter", "modelName from HTTP");
            // relative URLs must be resolved against URLBase by loadDescription()
            eq(device.getControlURL(), igd.base() + "/control", "controlURL resolved");
            eq(device.getPresentationURL(), igd.base() + "/index.html",
                    "presentationURL resolved");
        });

        test("GatewayDevice_http_read_timeout_api", () -> {
            eq(GatewayDevice.getHttpReadTimeout(), Integer.valueOf(7000),
                    "default HTTP read timeout");
            GatewayDevice.setHttpReadTimeout(1234);
            eq(GatewayDevice.getHttpReadTimeout(), Integer.valueOf(1234),
                    "timeout after set");
            GatewayDevice.setHttpReadTimeout(7000);
        });

        // ── discovery layer ──
        test("GatewayDiscover_constructors_and_constants", () -> {
            eq(GatewayDiscover.PORT, 1900, "SSDP port");
            eq(GatewayDiscover.IP, "239.255.255.250", "SSDP multicast address");
            check(new GatewayDiscover() != null, "default constructor");
            check(new GatewayDiscover("urn:schemas-upnp-org:device:InternetGatewayDevice:1") != null,
                    "single search-type constructor");
            check(new GatewayDiscover(new String[]{
                    "urn:schemas-upnp-org:device:InternetGatewayDevice:1",
                    "upnp:rootdevice"}) != null, "search-type array constructor");
        });

        test("GatewayDiscover_timeout_api", () -> {
            GatewayDiscover discover = new GatewayDiscover();
            eq(discover.getTimeout(), Integer.valueOf(3000), "default timeout");
            discover.setTimeout(1500);
            eq(discover.getTimeout(), Integer.valueOf(1500), "timeout after set");
        });

        test("GatewayDiscover_discover_live_network", () -> {
            GatewayDiscover discover = new GatewayDiscover();
            discover.setTimeout(800);
            Map<InetAddress, GatewayDevice> found;
            try {
                found = discover.discover();
            } catch (java.net.SocketException error) {
                throw new Skip("OHOS network stack refused the SSDP socket: " + error);
            }
            check(found != null, "discover() must never return null");
            check(discover.getAllGateways() != null, "getAllGateways() must never return null");
            eq(found.size(), discover.getAllGateways().size(),
                    "discover() and getAllGateways() agree");
            // getValidGateway() is null when no IGD answered — the contract is
            // " or a connected device", never an exception.
            GatewayDevice valid = discover.getValidGateway();
            check(valid == null || valid instanceof GatewayDevice, "getValidGateway() contract");
            System.out.println("       info: SSDP discovery returned " + found.size()
                    + " gateway(s) on this host");
        });

        // ── upstream runnable entry point (only upstream sample) ──
        test("Upstream_Main_entrypoint", () -> {
            Main.main(new String[0]);
        });

        // ── OHOS-specific cases ──
        test("OHOS_01_platform_jvm_identity", () -> {
            String osName = String.valueOf(System.getProperty("os.name")).toLowerCase();
            String osArch = String.valueOf(System.getProperty("os.arch")).toLowerCase();
            String vendor = String.valueOf(System.getProperty("java.vendor")).toLowerCase();
            String vmVendor = String.valueOf(System.getProperty("java.vm.vendor")).toLowerCase();
            String version = String.valueOf(System.getProperty("java.specification.version"));
            System.out.println("       info: os.name=" + osName + " os.arch=" + osArch
                    + " java.vendor=" + vendor + " java.vm.vendor=" + vmVendor
                    + " java.specification.version=" + version);
            check(osName.contains("harmony") || osName.contains("linux"),
                    "OHOS reports os.name harmonyos/linux, got " + osName);
            check(osArch.contains("aarch64") || osArch.contains("arm"),
                    "OHOS PC is aarch64, got " + osArch);
            int major = Integer.parseInt(version.split("\\.")[0]);
            check(major >= 17, "OHOS toolchain provides JDK 17+, got " + version);
            if (osName.contains("harmony")) {
                check(vendor.contains("bisheng") || vmVendor.contains("bisheng"),
                        "OHOS platform must run on BiSheng JDK, got vendor=" + vendor
                                + " vm=" + vmVendor);
            }
        });

        test("OHOS_02_ssdp_multicast_transport", () -> {
            eq(GatewayDiscover.IP, "239.255.255.250", "SSDP group address used by weupnp");
            eq(GatewayDiscover.PORT, 1900, "SSDP port used by weupnp");
            DatagramSocket socket = new DatagramSocket();
            try {
                socket.setSoTimeout(1200);
                String message = "M-SEARCH * HTTP/1.1\r\n"
                        + "HOST: " + GatewayDiscover.IP + ":" + GatewayDiscover.PORT + "\r\n"
                        + "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                        + "MAN: \"ssdp:discover\"\r\nMX: 2\r\n\r\n";
                byte[] payload = message.getBytes("UTF-8");
                socket.send(new DatagramPacket(payload, payload.length,
                        InetAddress.getByName(GatewayDiscover.IP), GatewayDiscover.PORT));
                check(socket.isBound(), "SSDP socket must stay bound after send");
                check(socket.getSoTimeout() == 1200, "SSDP socket timeout honoured");
                byte[] reply = new byte[1500];
                try {
                    socket.receive(new DatagramPacket(reply, reply.length));
                    System.out.println("       info: SSDP reply received on this OHOS host");
                } catch (java.net.SocketTimeoutException expected) {
                    System.out.println("       info: SSDP send OK, no IGD replied within 1200 ms");
                }
            } finally {
                socket.close();
            }
            check(socket.isClosed(), "SSDP socket closed cleanly");
        });

        test("OHOS_03_packaged_jar_loads_on_ohos_jvm", () -> {
            String jarPath = System.getProperty("weupnp.jar");
            check(jarPath != null && !jarPath.isEmpty(),
                    "weupnp.jar system property must point at the packaged JAR");
            File jarFile = new File(jarPath);
            check(jarFile.isFile(), "packaged JAR not found: " + jarPath);
            check(jarPath.endsWith("libexec/weupnp-0.1.4.jar"),
                    "JAR must be installed under libexec/, got " + jarPath);

            String[] classes = {
                "org.bitlet.weupnp.GatewayDevice",
                "org.bitlet.weupnp.GatewayDeviceHandler",
                "org.bitlet.weupnp.GatewayDiscover",
                "org.bitlet.weupnp.Main",
                "org.bitlet.weupnp.NameValueHandler",
                "org.bitlet.weupnp.PortMappingEntry",
            };
            URLClassLoader loader = new URLClassLoader(
                    new URL[]{jarFile.toURI().toURL()}, null);
            try {
                for (String name : classes) {
                    check(Class.forName(name, false, loader) != null,
                            "class not loadable by the OHOS JVM: " + name);
                }
            } catch (UnsatisfiedLinkError error) {
                throw new AssertionError("OHOS JVM failed to link a weupnp class: " + error);
            } finally {
                loader.close();
            }

            // bytecode level and OSGi headers must be consumable on OHOS
            JarFile jar = new JarFile(jarFile);
            try {
                Manifest manifest = jar.getManifest();
                eq(manifest.getMainAttributes().getValue("Bundle-SymbolicName"),
                        "org.bitlet.weupnp", "OSGi Bundle-SymbolicName");
                contains(manifest.getMainAttributes().getValue("Export-Package"),
                        "org.bitlet.weupnp", "OSGi Export-Package");
                contains(manifest.getMainAttributes().getValue("Import-Package"),
                        "org.xml.sax", "OSGi Import-Package");
                boolean license = false;
                Enumeration<JarEntry> entries = jar.entries();
                while (entries.hasMoreElements()) {
                    if ("license.txt".equals(entries.nextElement().getName())) {
                        license = true;
                    }
                }
                check(license, "license.txt must be bundled inside the JAR");

                int checked = 0;
                for (String name : classes) {
                    JarEntry entry = jar.getJarEntry(name.replace('.', '/') + ".class");
                    check(entry != null, "class file missing in JAR: " + name);
                    InputStream stream = jar.getInputStream(entry);
                    try {
                        byte[] header = new byte[8];
                        int read = 0;
                        while (read < 8) {
                            int step = stream.read(header, read, 8 - read);
                            if (step < 0) {
                                break;
                            }
                            read += step;
                        }
                        eq(read, 8, "truncated class header for " + name);
                        int major = ((header[6] & 0xff) << 8) | (header[7] & 0xff);
                        check(major <= 52,
                                "class " + name + " has bytecode version " + major
                                        + " > 52 (Java 8); the OHOS JVM target requires <= 52");
                        checked++;
                    } finally {
                        stream.close();
                    }
                }
                eq(checked, classes.length, "bytecode version checked for every class");
            } finally {
                jar.close();
            }
        });
    }

    // ── entry point ───────────────────────────────────────────────────────────

    public static void main(String[] args) throws Exception {
        System.out.println("=== weupnp 0.1.4 consumer test suite ===");
        System.out.println("    packaged JAR: " + System.getProperty("weupnp.jar"));
        runCases();
        System.out.println();
        System.out.println("================ weupnp test summary ================");
        System.out.println("total=" + total + " passed=" + passed
                + " failed=" + failed + " skipped=" + skipped);
        for (String name : failedNames) {
            System.out.println("  FAILED : " + name);
        }
        for (String name : skippedNames) {
            System.out.println("  SKIPPED: " + name);
        }
        System.out.println("WEUPNP_TEST_SUMMARY total=" + total + " passed=" + passed
                + " failed=" + failed + " skipped=" + skipped);
        if (failed > 0) {
            System.exit(1);
        }
    }
}
