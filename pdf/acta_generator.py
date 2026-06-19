# ══════════════════════════════════════════════════════════════
#  GENERADOR DE ACTA PDF — SISTEMA DE ASISTENCIA HGP
#  Hospital General Puyo — MSP Ecuador
#  Dependencias: pip install reportlab
#  Uso: python acta_generator.py --cod REU-4821 --url https://...
# ══════════════════════════════════════════════════════════════

import json
import argparse
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                 Paragraph, Spacer, Table, TableStyle,
                                 HRFlowable)

# ── COLORES INSTITUCIONALES ──
AZ  = colors.HexColor("#0B2545")
AZ2 = colors.HexColor("#163A6B")
VD  = colors.HexColor("#00A86B")
VDL = colors.HexColor("#E8F8F2")
RJ  = colors.HexColor("#C0392B")
RJL = colors.HexColor("#FEE8E6")
AM  = colors.HexColor("#D97706")
AML = colors.HexColor("#FFFBEB")
G1  = colors.HexColor("#E4EAF3")
G3  = colors.HexColor("#7D90A8")
G4  = colors.HexColor("#3D526A")
W   = colors.white
BLK = colors.black

# ── DIMENSIONES A4 ──
W_PAGE, H_PAGE = A4
ML = MR = 1.8 * cm
MT = 1.5 * cm
MB = 1.8 * cm
TW = W_PAGE - ML - MR

# ── ESTILOS ──
def sty(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9, leading=12,
                textColor=BLK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = {
    "inst":   sty("inst",  fontName="Helvetica-Bold", fontSize=6.5, textColor=G3,  alignment=TA_CENTER, leading=9),
    "hosp":   sty("hosp",  fontName="Helvetica-Bold", fontSize=10,  textColor=AZ,  alignment=TA_CENTER, leading=13),
    "dprov":  sty("dprov", fontName="Helvetica",      fontSize=8,   textColor=G4,  alignment=TA_CENTER, leading=11),
    "title":  sty("title", fontName="Helvetica-Bold", fontSize=11,  textColor=AZ,  alignment=TA_CENTER, leading=14, spaceBefore=4, spaceAfter=2),
    "sub":    sty("sub",   fontName="Helvetica",      fontSize=8,   textColor=G3,  alignment=TA_CENTER, leading=11, spaceAfter=6),
    "label":  sty("label", fontName="Helvetica-Bold", fontSize=7.5, textColor=G3,  leading=10),
    "val":    sty("val",   fontName="Helvetica",      fontSize=8.5, textColor=AZ,  leading=11),
    "sec":    sty("sec",   fontName="Helvetica-Bold", fontSize=8,   textColor=W,   alignment=TA_LEFT,   leading=11),
    "th":     sty("th",    fontName="Helvetica-Bold", fontSize=7.5, textColor=AZ,  alignment=TA_CENTER, leading=10),
    "td":     sty("td",    fontName="Helvetica",      fontSize=8,   textColor=AZ,  alignment=TA_LEFT,   leading=10),
    "tdc":    sty("tdc",   fontName="Helvetica",      fontSize=8,   textColor=AZ,  alignment=TA_CENTER, leading=10),
    "ley":    sty("ley",   fontName="Helvetica",      fontSize=6.2, textColor=G4,  alignment=TA_JUSTIFY,leading=8.5),
    "leyb":   sty("leyb",  fontName="Helvetica-Bold", fontSize=7,   textColor=AZ,  alignment=TA_LEFT,   leading=10),
    "small":  sty("small", fontName="Helvetica",      fontSize=6.5, textColor=G3,  alignment=TA_CENTER, leading=9),
    "obs":    sty("obs",   fontName="Helvetica",      fontSize=8,   textColor=G4,  leading=11),
    "stats":  sty("stats", fontName="Helvetica",      fontSize=7.5, textColor=G4,  leading=10, spaceBefore=2, spaceAfter=4),
    "firma_l":sty("fl",    fontName="Helvetica",      fontSize=7.5, textColor=G3,  leading=10),
    "firma_n":sty("fn",    fontName="Helvetica-Bold", fontSize=9,   textColor=AZ,  leading=12),
    "firma_c":sty("fc",    fontName="Helvetica",      fontSize=8,   textColor=G4,  leading=11),
    "firma_i":sty("fi",    fontName="Helvetica",      fontSize=7.5, textColor=G3,  leading=10),
    "no":     sty("no",    fontName="Helvetica",      fontSize=8,   textColor=G3,  leading=11),
}


def qr_placeholder(c, x, y, size=1.8*cm):
    """Dibuja un QR placeholder. En producción reemplazar con qrcode real."""
    c.setStrokeColor(AZ); c.setFillColor(W); c.setLineWidth(0.8)
    c.rect(x, y, size, size, fill=1)
    c.setFillColor(AZ)
    cell = size / 7
    pattern = [
        (0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),
        (0,1),(6,1),(0,2),(2,2),(3,2),(4,2),(6,2),
        (0,3),(6,3),(0,4),(2,4),(3,4),(4,4),(6,4),
        (0,5),(6,5),(0,6),(1,6),(2,6),(3,6),(4,6),(5,6),(6,6),
    ]
    for col, row in pattern:
        c.rect(x+col*cell, y+row*cell, cell*0.82, cell*0.82, fill=1, stroke=0)
    c.setFont("Helvetica", 5); c.setFillColor(G3)
    c.drawCentredString(x+size/2, y-0.3*cm, "Escanear para verificar")


class ActaDoc(BaseDocTemplate):
    """Documento con membrete y pie en cada página."""

    def __init__(self, filename, reunion, **kwargs):
        super().__init__(filename, **kwargs)
        self.reunion = reunion
        frame = Frame(ML, MB, TW, H_PAGE - MT - MB, id="main")
        template = PageTemplate(id="acta", frames=[frame], onPage=self._draw_page)
        self.addPageTemplates([template])

    def _draw_page(self, canv, doc):
        canv.saveState()
        r = self.reunion
        y_top = H_PAGE - MT

        # ── Logos placeholder ──
        lw, lh = 1.8*cm, 1.55*cm
        for x_logo, label in [(ML, "MSP"), (W_PAGE-MR-lw, "HGP")]:
            canv.setFillColor(G1); canv.setStrokeColor(G1)
            canv.roundRect(x_logo, y_top-lh, lw, lh, 4, fill=1, stroke=0)
            canv.setFillColor(G3); canv.setFont("Helvetica-Bold", 6)
            canv.drawCentredString(x_logo+lw/2, y_top-lh/2+0.12*cm, "LOGO")
            canv.drawCentredString(x_logo+lw/2, y_top-lh/2-0.18*cm, label)

        # ── Texto membrete ──
        cx = W_PAGE / 2
        canv.setFillColor(G3); canv.setFont("Helvetica-Bold", 6.5)
        canv.drawCentredString(cx, y_top-0.42*cm, "MINISTERIO DE SALUD PÚBLICA DEL ECUADOR")
        canv.setFillColor(AZ); canv.setFont("Helvetica-Bold", 9.5)
        canv.drawCentredString(cx, y_top-0.82*cm, "Hospital General Puyo")
        canv.setFillColor(G4); canv.setFont("Helvetica", 7.5)
        canv.drawCentredString(cx, y_top-1.12*cm, "Dirección Provincial de Salud de Pastaza")

        # ── Líneas separadoras ──
        sep_y = y_top - lh - 0.12*cm
        canv.setStrokeColor(AZ); canv.setLineWidth(1.2)
        canv.line(ML, sep_y, W_PAGE-MR, sep_y)
        canv.setStrokeColor(VD); canv.setLineWidth(2.5)
        canv.line(ML, sep_y-0.18*cm, W_PAGE-MR, sep_y-0.18*cm)

        # ── Pie de página ──
        pie_y = MB - 0.15*cm
        canv.setStrokeColor(G1); canv.setLineWidth(0.4)
        canv.line(ML, pie_y+0.5*cm, W_PAGE-MR, pie_y+0.5*cm)

        # QR
        qs = 1.8*cm
        qr_x = W_PAGE - MR - qs
        qr_placeholder(canv, qr_x, pie_y-1.25*cm, qs)

        # Leyenda
        ley_w = TW - qs - 0.5*cm
        leyenda = (
            "<b>Leyenda de validez administrativa:</b> El presente registro fue generado mediante el "
            "Sistema Institucional de Registro de Reuniones del Hospital General Puyo — MSP Ecuador. "
            "Las asistencias corresponden a registros digitales autenticados con credenciales "
            "institucionales personales e intransferibles, con timestamp de servidor. "
            "Este documento tiene validez administrativa interna conforme a los procedimientos institucionales vigentes."
        )
        p = Paragraph(leyenda, S["ley"])
        p.wrapOn(canv, ley_w, 3*cm)
        p.drawOn(canv, ML, pie_y-0.82*cm)

        # Línea inferior
        canv.setFont("Helvetica", 6); canv.setFillColor(G3)
        canv.drawString(ML, pie_y+0.15*cm,
                        f"Generado: {r.get('tsGenerado','—')}   ·   Código: {r.get('codigo','—')}   ·   Sistema de Registro HGP v1.0")
        canv.drawRightString(W_PAGE-MR, pie_y+0.15*cm, f"Pág. {doc.page}")

        canv.restoreState()


def campo(label, valor):
    return [Paragraph(label, S["label"]), Paragraph(str(valor or "—"), S["val"])]


def seccion_header(texto, color=AZ):
    t = Table([[Paragraph(f"  {texto}", S["sec"])]], colWidths=[TW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), color),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
    ]))
    return t


def generar_acta(reunion, convocados, asistentes, output_path):
    """
    Genera el PDF del acta de asistencia.

    Args:
        reunion (dict): datos de la reunión
        convocados (list): lista de convocados [{nombre, cargo, area}]
        asistentes (list): lista de asistentes registrados [{nombre, cargo, hora, tipo}]
        output_path (str): ruta de salida del PDF
    """
    doc = ActaDoc(
        output_path,
        reunion=reunion,
        pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT + 2.2*cm,
        bottomMargin=MB + 2.1*cm
    )

    story = []

    # ── TÍTULO ──
    story.append(Paragraph("ACTA DE REGISTRO DE ASISTENCIA", S["title"]))
    story.append(Paragraph("Reunión Institucional — Hospital General Puyo", S["sub"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=G1, spaceAfter=6))

    # ── DATOS DE LA REUNIÓN ──
    obs_fmt = (reunion.get("obs") or "—").replace("\n", "<br/>")
    datos = [
        campo("Código de reunión",            reunion.get("codigo")),
        campo("N.° Memorando / convocatoria", reunion.get("memo") or "—"),
        campo("Asunto / tema",                reunion.get("tema")),
        campo("Fecha y hora de inicio",       reunion.get("fechaI")),
        campo("Hora estimada de fin",         reunion.get("fechaF")),
        campo("Hora real de cierre",          reunion.get("tsCierre") or "Reunión aún activa"),
        campo("Lugar",                        reunion.get("lugar")),
        campo("Convocado por",                reunion.get("convoca")),
        [Paragraph("Orden del día", S["label"]), Paragraph(obs_fmt, S["obs"])],
    ]
    t_datos = Table(datos, colWidths=[3.6*cm, TW-3.6*cm])
    t_datos.setStyle(TableStyle([
        ("VALIGN",          (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",      (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",   (0,0),(-1,-1), 3),
        ("LEFTPADDING",     (0,0),(-1,-1), 0),
        ("RIGHTPADDING",    (0,0),(-1,-1), 0),
        ("LINEBELOW",       (0,0),(-1,-2), 0.3, G1),
        ("BACKGROUND",      (0,0),(0,-1), colors.HexColor("#F8FAFD")),
        ("LEFTPADDING",     (0,0),(0,-1), 6),
    ]))
    story.append(t_datos)
    story.append(Spacer(1, 0.4*cm))

    # ── SECCIÓN A: CONVOCADOS ──
    story.append(seccion_header("SECCIÓN A — CONVOCADOS", AZ))
    story.append(Spacer(1, 0.15*cm))

    asist_dict = {a["nombre"]: a for a in asistentes if a.get("tipo") == "convocado"}
    asist_total = len(asist_dict)
    ausentes    = len(convocados) - asist_total

    story.append(Paragraph(
        f"Total convocados: <b>{len(convocados)}</b>   ·   "
        f"Asistieron: <b>{asist_total}</b>   ·   "
        f"Ausentes: <b>{ausentes}</b>",
        S["stats"]
    ))

    hdr_a = [Paragraph(h, S["th"]) for h in ["N.°", "Nombre completo", "Cargo / Área", "Asistió", "Hora"]]
    rows_a = [hdr_a]
    ts_a_extra = []
    for i, c in enumerate(convocados):
        a = asist_dict.get(c["nombre"])
        check_color = "#00A86B" if a else "#C0392B"
        check_txt   = "✓" if a else "✗"
        rows_a.append([
            Paragraph(str(i+1), S["tdc"]),
            Paragraph(c["nombre"], S["td"]),
            Paragraph(f"{c['cargo']}<br/><font color='#7D90A8' size='7'>{c.get('area','')}</font>", S["td"]),
            Paragraph(f"<font color='{check_color}'><b>{check_txt}</b></font>", S["tdc"]),
            Paragraph(a["hora"] if a else "—", S["tdc"]),
        ])
        if not a:
            ts_a_extra.append(("BACKGROUND", (0, i+1), (-1, i+1), colors.HexColor("#FFF8F8")))

    t_a = Table(rows_a, colWidths=[0.7*cm, 5.8*cm, 5.5*cm, 1.3*cm, 1.5*cm], repeatRows=1)
    ts_a = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), AZ2),
        ("TEXTCOLOR",     (0,0),(-1,0), W),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 7.5),
        ("ALIGN",         (0,0),(-1,0), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [W, colors.HexColor("#F8FAFD")]),
        ("GRID",          (0,0),(-1,-1), 0.3, G1),
        ("LINEBELOW",     (0,0),(-1,0), 1.0, AZ),
    ])
    for cmd in ts_a_extra:
        ts_a.add(*cmd)
    t_a.setStyle(ts_a)
    story.append(t_a)
    story.append(Spacer(1, 0.4*cm))

    # ── SECCIÓN B: ADICIONALES ──
    story.append(seccion_header("SECCIÓN B — ASISTENTES ADICIONALES (no convocados)", AM))
    story.append(Spacer(1, 0.15*cm))

    adic = [a for a in asistentes if a.get("tipo") == "adicional"]
    if adic:
        hdr_b = [Paragraph(h, S["th"]) for h in ["N.°", "Nombre completo", "Cargo / Área", "Hora"]]
        rows_b = [hdr_b]
        for i, a in enumerate(adic):
            rows_b.append([
                Paragraph(str(i+1), S["tdc"]),
                Paragraph(a["nombre"], S["td"]),
                Paragraph(f"{a['cargo']}<br/><font color='#7D90A8' size='7'>{a.get('area','')}</font>", S["td"]),
                Paragraph(a["hora"], S["tdc"]),
            ])
        t_b = Table(rows_b, colWidths=[0.7*cm, 6.0*cm, 6.3*cm, 1.8*cm], repeatRows=1)
        t_b.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), colors.HexColor("#92400E")),
            ("TEXTCOLOR",     (0,0),(-1,0), W),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,0), 7.5),
            ("ALIGN",         (0,0),(-1,0), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 4),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [W, colors.HexColor("#FFFBF0")]),
            ("GRID",          (0,0),(-1,-1), 0.3, G1),
            ("LINEBELOW",     (0,0),(-1,0), 1.0, AM),
        ]))
        story.append(t_b)
    else:
        story.append(Paragraph("No se registraron asistentes adicionales.", S["no"]))

    story.append(Spacer(1, 0.5*cm))

    # ── FIRMA / GENERADO POR ──
    firma_data = [
        [Paragraph("Generado y certificado por:", S["firma_l"]), ""],
        [Paragraph(f"<b>{reunion.get('creador','—')}</b>", S["firma_n"]), ""],
        [Paragraph(reunion.get("creadorCargo","—"), S["firma_c"]), ""],
        [Paragraph("Hospital General Puyo — MSP Ecuador", S["firma_i"]), ""],
    ]
    t_firma = Table(firma_data, colWidths=[TW*0.6, TW*0.4])
    t_firma.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("LINEABOVE",     (0,0),(0,0), 0.8, AZ),
        ("TOPPADDING",    (0,0),(0,0), 6),
    ]))
    story.append(t_firma)

    doc.build(story)
    print(f"✅ PDF generado: {output_path}")


# ── DATOS DEMO ──
DEMO_REUNION = {
    "codigo":       "REU-4821",
    "memo":         "MSP-HGP-2026-0247-M",
    "tema":         "Comité de Farmacia y Terapéutica — Junio 2026",
    "fechaI":       "18/06/2026 09:00",
    "fechaF":       "18/06/2026 11:00",
    "tsCierre":     "18/06/2026 10:47",
    "lugar":        "Sala de Reuniones — Dirección Asistencial, HGP",
    "convoca":      "Director Asistencial (e)",
    "obs":          "1. Revisión del listado básico de medicamentos 2026\n2. Aprobación de protocolo de sedoanalgesia\n3. Reporte de Farmacovigilancia Q1-2026\n4. Varios",
    "creador":      "Alex Andrés Naranjo Andrade",
    "creadorCargo": "Director Asistencial (e)",
    "tsGenerado":   "18/06/2026 11:03",
}
DEMO_CONVOCADOS = [
    {"nombre": "Alex Andrés Naranjo Andrade",  "cargo": "Director Asistencial (e)",  "area": "Dirección Asistencial"},
    {"nombre": "Juan Pérez López",             "cargo": "Médico Residente",          "area": "Emergencias"},
    {"nombre": "María Rodríguez Torres",       "cargo": "Enfermera Líder",           "area": "Hospitalización"},
    {"nombre": "Luis Gómez Vargas",            "cargo": "BQF Farmacéutico",          "area": "Farmacia"},
    {"nombre": "Carmen Coordinadora Silva",    "cargo": "Jefa de Enfermería",        "area": "Enfermería"},
    {"nombre": "Roberto Andrade Morales",      "cargo": "Médico Especialista",       "area": "Cirugía"},
    {"nombre": "Lucía Vargas Cevallos",        "cargo": "Trabajadora Social",        "area": "Trabajo Social"},
]
DEMO_ASISTENTES = [
    {"nombre": "Alex Andrés Naranjo Andrade",  "cargo": "Director Asistencial (e)",  "hora": "09:02", "tipo": "convocado"},
    {"nombre": "Juan Pérez López",             "cargo": "Médico Residente",          "hora": "09:05", "tipo": "convocado"},
    {"nombre": "Luis Gómez Vargas",            "cargo": "BQF Farmacéutico",          "hora": "09:08", "tipo": "convocado"},
    {"nombre": "Carmen Coordinadora Silva",    "cargo": "Jefa de Enfermería",        "hora": "09:11", "tipo": "convocado"},
    {"nombre": "Lucía Vargas Cevallos",        "cargo": "Trabajadora Social",        "hora": "09:15", "tipo": "convocado"},
    {"nombre": "Pedro Salazar Mora",           "cargo": "Interno de Medicina",       "hora": "09:20", "tipo": "adicional"},
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de acta PDF — HGP")
    parser.add_argument("--demo",   action="store_true", help="Generar acta con datos demo")
    parser.add_argument("--output", default="acta_HGP.pdf", help="Ruta de salida del PDF")
    parser.add_argument("--data",   help="JSON con {reunion, convocados, asistentes}")
    args = parser.parse_args()

    if args.demo or not args.data:
        generar_acta(DEMO_REUNION, DEMO_CONVOCADOS, DEMO_ASISTENTES, args.output)
    else:
        with open(args.data, "r", encoding="utf-8") as f:
            d = json.load(f)
        generar_acta(d["reunion"], d["convocados"], d["asistentes"], args.output)
