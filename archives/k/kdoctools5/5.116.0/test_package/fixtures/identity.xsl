<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" />
  <xsl:template match="/">
    <html>
      <body>
        <h1><xsl:value-of select="/article/title" /></h1>
        <p><xsl:value-of select="/article/para" /></p>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
