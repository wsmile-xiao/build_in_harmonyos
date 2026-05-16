# xmlstarlet

Command-line XML toolkit for transformation, validation, parsing, and editing XML documents.

## Features
- XML transformation (XSLT)
- XML validation
- XML parsing and querying
- XML editing and formatting

## Usage
```bash
xmlstarlet sel -t -v "//element" file.xml  # Select element value
xmlstarlet ed -d "//element" file.xml      # Delete element
xmlstarlet val file.xml                    # Validate XML
```

## Version
- 1.6.1 (compiled 2026-05-15)

## Dependencies
- libxml2 >= 2.15.0
- libxslt >= 1.1.42
