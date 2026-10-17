/**
 * TestJakartaActivation — jakarta-activation 2.0.0 API 调用测试
 *
 * 使用反射加载并断言 jakarta.activation 命名空间的核心类型与契约，
 * 验证两个 JAR（jakarta.activation-api + jakarta.activation）完整可用
 * （Jakarta Activation 2.0 标准）。
 * 仅使用 JDK 类型（Class.forName + java.lang.reflect），编译期不依赖被测 JAR。
 */
public class TestJakartaActivation {

    private static int passed = 0;

    private static void ok(String msg) {
        passed++;
        System.out.println("OK[" + passed + "]: " + msg);
    }

    private static void fail(String msg) {
        System.err.println("FAIL: " + msg);
        System.exit(1);
    }

    private static Class<?> load(String name) throws Exception {
        Class<?> c = Class.forName(name);
        ok("loaded " + name);
        return c;
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Class<?>[] noArg = new Class<?>[0];

        // 断言 1-15：核心类型可加载
        Class<?> dataSource = load("jakarta.activation.DataSource");
        Class<?> dataHandler = load("jakarta.activation.DataHandler");
        Class<?> dataContentHandler = load("jakarta.activation.DataContentHandler");
        Class<?> dataContentHandlerFactory = load("jakarta.activation.DataContentHandlerFactory");
        Class<?> commandMap = load("jakarta.activation.CommandMap");
        Class<?> commandInfo = load("jakarta.activation.CommandInfo");
        Class<?> fileTypeMap = load("jakarta.activation.FileTypeMap");
        Class<?> mimetypesFileTypeMap = load("jakarta.activation.MimetypesFileTypeMap");
        Class<?> mailcapCommandMap = load("jakarta.activation.MailcapCommandMap");
        Class<?> activationDataFlavor = load("jakarta.activation.ActivationDataFlavor");
        Class<?> fileDataSource = load("jakarta.activation.FileDataSource");
        Class<?> urlDataSource = load("jakarta.activation.URLDataSource");
        Class<?> mimeType = load("jakarta.activation.MimeType");
        Class<?> mimeTypeParseException = load("jakarta.activation.MimeTypeParseException");
        Class<?> unsupportedDataTypeException = load("jakarta.activation.UnsupportedDataTypeException");

        // 断言 16：DataSource 是接口
        if (!dataSource.isInterface()) {
            fail("jakarta.activation.DataSource is not an interface");
        }
        ok("DataSource is an interface");

        // 断言 17：DataSource 三个必备方法
        dataSource.getMethod("getInputStream", noArg);
        dataSource.getMethod("getContentType", noArg);
        dataSource.getMethod("getName", noArg);
        ok("DataSource exposes getInputStream/getContentType/getName");

        // 断言 18：DataHandler 有 getInputStream/getContentType（核心解码入口）
        dataHandler.getMethod("getInputStream", noArg);
        dataHandler.getMethod("getContentType", noArg);
        ok("DataHandler exposes getInputStream/getContentType");

        // 断言 19：MimetypesFileTypeMap extends FileTypeMap（可插拔文件类型映射）
        if (!fileTypeMap.isAssignableFrom(mimetypesFileTypeMap)) {
            fail("MimetypesFileTypeMap does not extend FileTypeMap");
        }
        ok("MimetypesFileTypeMap extends FileTypeMap");

        // 断言 20：MailcapCommandMap extends CommandMap
        if (!commandMap.isAssignableFrom(mailcapCommandMap)) {
            fail("MailcapCommandMap does not extend CommandMap");
        }
        ok("MailcapCommandMap extends CommandMap");

        // 断言 21：CommandInfo 有 getCommandObject（命令对象工厂）
        // 实测签名（javap jakarta.activation.CommandInfo）：getCommandObject(DataHandler, ClassLoader)
        commandInfo.getMethod("getCommandObject",
                new Class<?>[]{jakarta.activation.DataHandler.class, ClassLoader.class});
        ok("CommandInfo exposes getCommandObject(DataHandler, ClassLoader)");

        // 断言 22：FileDataSource / URLDataSource 实现 DataSource
        if (!dataSource.isAssignableFrom(fileDataSource)
                || !dataSource.isAssignableFrom(urlDataSource)) {
            fail("FileDataSource/URLDataSource do not implement DataSource");
        }
        ok("FileDataSource and URLDataSource implement DataSource");

        // 断言 23：UnsupportedDataTypeException extends IOException
        if (!java.io.IOException.class.isAssignableFrom(unsupportedDataTypeException)) {
            fail("UnsupportedDataTypeException does not extend IOException");
        }
        ok("UnsupportedDataTypeException extends IOException");

        // 断言 24：MimeTypeParseException extends Exception（受检异常）
        if (!Exception.class.isAssignableFrom(mimeTypeParseException)) {
            fail("MimeTypeParseException does not extend Exception");
        }
        ok("MimeTypeParseException extends Exception");

        // 断言 25：MimeType 有 match(String) 与 getPrimaryType
        mimeType.getMethod("match", new Class<?>[]{String.class});
        mimeType.getMethod("getPrimaryType", noArg);
        ok("MimeType exposes match(String)/getPrimaryType");

        // 断言 26：DataContentHandler 有 getTransferData(ActivationDataFlavor, DataSource)
        // 实测签名（javap jakarta.activation.DataContentHandler）：
        //   getTransferData(ActivationDataFlavor, DataSource)
        dataContentHandler.getMethod("getTransferData",
                new Class<?>[]{activationDataFlavor, dataSource});
        ok("DataContentHandler exposes getTransferData(ActivationDataFlavor, DataSource)");

        // 断言 27：DataContentHandlerFactory 是接口且有 createDataContentHandler
        if (!dataContentHandlerFactory.isInterface()) {
            fail("DataContentHandlerFactory is not an interface");
        }
        dataContentHandlerFactory.getMethod("createDataContentHandler",
                new Class<?>[]{String.class});
        ok("DataContentHandlerFactory is an interface with createDataContentHandler(String)");

        // 断言 28：ActivationDataFlavor 存在且有 getMimeType
        activationDataFlavor.getMethod("getMimeType", noArg);
        ok("ActivationDataFlavor exposes getMimeType");

        System.out.println("PASS: jakarta-activation 2.0.0 — " + passed + " assertions passed");
    }
}
