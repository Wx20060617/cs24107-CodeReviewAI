# -*- coding: utf-8 -*-
"""
EA 图导出（最终方案）：用 Diagram.SaveAsPDF 直接导出每张图 -> 白底、无水印，
再由 PyMuPDF 转成 PNG。彻底规避：①试用版水印 ②截图黑屏 ③连线交叉（布局已在建模脚本修好）。

用法：
    python tools/ea_export_pdf.py            # 导出全部 7 张
    python tools/ea_export_pdf.py 2-6        # 只导出名字含 2-6 的
"""
import os, sys, time
import win32com.client as w
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
EAP  = os.path.join(BASE, "model", "CodeReviewAI.eap")
OUT  = os.path.join(BASE, "assets", "lab2", "ea")
TMP  = os.path.join(BASE, "model", "_pdf")
LOG  = os.path.join(BASE, "model", "_export.log")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

SLUGS = {
    "2-1": "fig2-1-context",
    "2-2": "fig2-2-dfd-top",
    "2-3": "fig2-3-dfd-0",
    "2-4": "fig2-4-dfd-1",
    "2-5": "fig2-5-usecase",
    "2-6": "fig2-6-class",
    "2-7": "fig2-7-sequence",
}

_f = open(LOG, "w", encoding="utf-8")
def p(*a):
    print(*a, file=_f); _f.flush(); print(*a)


def collect_diagrams(pkg, acc):
    for i in range(pkg.Diagrams.Count):
        acc.append(pkg.Diagrams.GetAt(i))
    for i in range(pkg.Packages.Count):
        collect_diagrams(pkg.Packages.GetAt(i), acc)


def pdf_to_png(pdf_path, out_png):
    doc = pymupdf.open(pdf_path)
    # 取第一页（EA SaveAsPDF 通常一页一图）
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pix.save(out_png)
    doc.close()
    return pix.width, pix.height


def crop_png(png_path):
    """裁掉空白边（EA 导出为 A4 整页，图只在顶部），保留 18px 白边"""
    from PIL import Image
    import numpy as np
    im = Image.open(png_path).convert("RGB")
    a = np.asarray(im)
    nonwhite = a.min(axis=2) < 200
    ys, xs = np.nonzero(nonwhite)
    if len(xs) == 0:
        return im.size
    m = 18
    x0 = max(0, int(xs.min()) - m)
    x1 = min(im.width, int(xs.max()) + m)
    y0 = max(0, int(ys.min()) - m)
    y1 = min(im.height, int(ys.max()) + m)
    im.crop((x0, y0, x1, y1)).save(png_path)
    return (x1 - x0, y1 - y0)


def _win32():
    import win32com.client
    return win32com.client


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    p("=== EA SaveAsPDF 导出", time.strftime("%H:%M:%S"))

    wc = _win32()
    app = wc.Dispatch("EA.App")
    repo = app.Repository
    p("OpenFile:", repo.OpenFile(EAP))
    time.sleep(2.5)

    diags = []
    collect_diagrams(repo.Models.GetAt(0), diags)
    p("diagrams:", [d.Name for d in diags])

    ok = 0
    for d in diags:
        if only and only not in d.Name:
            continue
        key = next((k for k in SLUGS if k in d.Name), None)
        slug = SLUGS.get(key, "figX-" + d.Name[:12].replace(" ", "_"))
        pdf = os.path.join(TMP, slug + ".pdf")
        png = os.path.join(OUT, slug + ".png")
        try:
            d.SaveAsPDF(pdf)
            if not os.path.exists(pdf) or os.path.getsize(pdf) < 1000:
                p("!! SaveAsPDF 结果异常", slug); continue
            pw, ph = pdf_to_png(pdf, png)
            cw, ch = crop_png(png)
            p("ok", slug, f"raw={pw}x{ph} crop={cw}x{ch}")
            ok += 1
        except Exception as e:
            p("FAIL", slug, str(e)[:140])
    p("DONE", ok, "张", time.strftime("%H:%M:%S"))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        import traceback
        p("FATAL:", e); p(traceback.format_exc()[:1200]); rc = 9
    _f.close()
    os._exit(rc)
