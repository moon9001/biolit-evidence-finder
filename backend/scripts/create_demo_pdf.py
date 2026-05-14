"""Create a small demo PDF with botanical content for testing.

Usage:
    python scripts/create_demo_pdf.py
Output:
    ../data/uploads/demo_camellia.pdf  (NOT auto-loaded)
or simply:
    python scripts/create_demo_pdf.py demo.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF


PAGE_TEXTS = [
    (
        "BioLitEvidence Finder Demo Volume\n"
        "Notes on Chinese Tea Plants and Camellia\n\n"
        "This demonstration document is generated for testing the page-level "
        "evidence discovery prototype. It contains a few species and locality "
        "names for indexing tests."
    ),
    (
        "1. Camellia sinensis\n"
        "Camellia sinensis (L.) Kuntze 是世界上最重要的经济作物之一，"
        "中文常称茶树。本种在中国云南、四川、贵州、广东等地广泛栽培。"
        "茶树的花期一般为 10 月至次年 2 月，果期 9 至 10 月。\n\n"
        "Voucher specimen: KIB 0123456 (Yunnan, Lincang)."
    ),
    (
        "2. Camellia reticulata\n"
        "Camellia reticulata Lindl. var. reticulata 主要分布于云南滇中、"
        "滇西，海拔 1500-2800 m 的常绿阔叶林中。云南山茶花是著名的观赏植物，"
        "图版 II 给出了花和叶的形态图说。"
    ),
    (
        "3. Rosa chinensis\n"
        "Rosa chinensis Jacq. 月季，中国传统名花。本志记录的标本来自湖南、"
        "湖北、四川等地。R. chinensis var. spontanea 为野生类型，"
        "见于秦巴山区。"
    ),
    (
        "Index of Scientific Names\n"
        "Camellia sinensis ............ 2\n"
        "Camellia reticulata ........... 3\n"
        "Rosa chinensis ................ 4\n"
        "References:\n"
        "Flora of China, vol. 12. 中国植物志, 第十二卷.\n"
    ),
]


def build_pdf(out_path: Path) -> None:
    doc = fitz.open()
    for i, body in enumerate(PAGE_TEXTS, start=1):
        page = doc.new_page(width=595, height=842)  # A4
        # Use built-in font; PyMuPDF can render CJK via Helvetica fallback
        # if a CJK font is embedded. The demo text mixes ASCII + CJK; we
        # write it as text so the PDF text layer carries Unicode.
        rect = fitz.Rect(60, 70, 540, 780)
        text = f"Page {i}\n\n{body}"
        try:
            page.insert_textbox(
                rect,
                text,
                fontname="china-s",   # PyMuPDF embedded simplified CJK font
                fontsize=12,
                align=0,
            )
        except Exception:
            # Fallback to Helvetica (CJK chars become tofu but ASCII still ok)
            page.insert_textbox(rect, text, fontname="helv", fontsize=12)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_camellia.pdf")
    build_pdf(out)
    print(f"Wrote demo PDF to: {out.resolve()}")


if __name__ == "__main__":
    main()
