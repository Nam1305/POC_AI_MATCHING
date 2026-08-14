"""
Xlsx writer tối giản, chỉ dùng stdlib (zipfile + XML thô) — không kéo thêm
dependency (openpyxl/pandas) vào requirements.txt của service chỉ để phục vụ
1 script báo cáo. Đủ dùng cho bảng dữ liệu tĩnh: nhiều sheet, header in đậm,
số thực format 3 chữ số thập phân, độ rộng cột tự co theo nội dung.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheet_overrides}
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.000"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><sz val="11"/><name val="Calibri"/><b/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
</styleSheet>"""

_STYLE_HEADER = 1
_STYLE_FLOAT = 2


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell_xml(row_idx: int, col_idx: int, value) -> str:
    ref = f"{_col_letter(col_idx)}{row_idx}"
    is_header = row_idx == 1
    if isinstance(value, bool):
        value = str(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        style = f' s="{_STYLE_HEADER}"' if is_header else (f' s="{_STYLE_FLOAT}"' if isinstance(value, float) else "")
        return f'<c r="{ref}"{style}><v>{value}</v></c>'
    text = escape("" if value is None else str(value))
    style = f' s="{_STYLE_HEADER}"' if is_header else ""
    return f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(rows: list[list]) -> str:
    ncols = max((len(r) for r in rows), default=1)
    widths = [8] * ncols
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = min(max(widths[i], len(str(v)) + 2), 60)
    cols_xml = "".join(
        f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)
    )
    body = []
    for ridx, row in enumerate(rows, start=1):
        cells = "".join(_cell_xml(ridx, cidx, v) for cidx, v in enumerate(row, start=1))
        body.append(f'<row r="{ridx}">{cells}</row>')
    freeze = '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>' if rows else ""
    sheet_views = f'<sheetViews><sheetView workbookViewId="0">{freeze}</sheetView></sheetViews>' if rows else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols_xml}</cols>"
        f"{sheet_views}"
        f"<sheetData>{''.join(body)}</sheetData>"
        "</worksheet>"
    )


def write_xlsx(path: Path, sheets: dict[str, list[list]]) -> None:
    """sheets: {sheet_name: [[header...], [row1...], [row2...], ...]}. Hàng đầu = header (in đậm)."""
    names = list(sheets.keys())
    n = len(names)

    sheet_overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(n)
    )
    content_types = _CONTENT_TYPES.format(sheet_overrides=sheet_overrides)

    workbook_sheets = "\n".join(
        f'<sheet name="{escape(name[:31])}" sheetId="{i+1}" r:id="rId{i+1}"/>'
        for i, name in enumerate(names)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{workbook_sheets}</sheets>"
        "</workbook>"
    )

    wb_rels_entries = "\n".join(
        f'<Relationship Id="rId{i+1}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i+1}.xml"/>'
        for i in range(n)
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{wb_rels_entries}"
        f'<Relationship Id="rId{n+1}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        f'Target="styles.xml"/>'
        "</Relationships>"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", _STYLES)
        for i, name in enumerate(names):
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", _sheet_xml(sheets[name]))
