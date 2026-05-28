from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_fill_color(11, 31, 58)
        self.rect(0, 0, 210, 18, 'F')
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.set_y(5)
        self.cell(0, 8, 'ADVOCATEAI  |  Legal Document', align='C')
        self.set_text_color(0, 0, 0)
        self.ln(14)

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f'Page {self.page_no()} | Sample Document for AdvocateAI Testing | Confidential', align='C')

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(20, 22, 20)

def divider(p):
    p.set_draw_color(200, 210, 225)
    p.set_line_width(0.4)
    p.line(20, p.get_y(), 190, p.get_y())
    p.ln(4)

def section_header(p, text):
    p.set_fill_color(240, 244, 251)
    p.set_draw_color(30, 99, 233)
    p.set_line_width(0.8)
    p.set_font('Helvetica', 'B', 10)
    p.set_text_color(11, 31, 58)
    p.cell(0, 8, text, border='L', fill=True, ln=True)
    p.set_line_width(0.2)
    p.ln(2)

def body(p, text, size=10):
    p.set_font('Helvetica', '', size)
    p.set_text_color(50, 60, 75)
    p.multi_cell(0, 6, text)
    p.ln(2)

def highlight_box(p, label, value, color=(255, 243, 225)):
    p.set_fill_color(*color)
    p.set_draw_color(200, 150, 0)
    p.set_line_width(0.3)
    p.set_font('Helvetica', 'B', 10)
    p.set_text_color(100, 60, 0)
    p.cell(52, 8, label, border=1, fill=True)
    p.set_font('Helvetica', 'B', 10)
    p.set_text_color(180, 30, 30)
    p.cell(0, 8, value, border=1, fill=False, ln=True)
    p.ln(1)

# Title block
pdf.set_font('Helvetica', 'B', 17)
pdf.set_text_color(11, 31, 58)
pdf.cell(0, 10, 'MIETRECHTLICHE ABMAHNUNG', align='C', ln=True)
pdf.set_font('Helvetica', 'I', 10)
pdf.set_text_color(100, 120, 150)
pdf.cell(0, 6, 'Einschreiben mit Rueckschein  |  Formal Legal Warning', align='C', ln=True)
pdf.ln(4)
divider(pdf)

# Parties
col_w = 85
pdf.set_font('Helvetica', 'B', 9)
pdf.set_text_color(30, 99, 233)
pdf.cell(col_w, 6, 'ABSENDER (Vermieter / Landlord)', ln=False)
pdf.set_x(20 + col_w + 5)
pdf.cell(col_w, 6, 'EMPFAENGER (Mieter / Tenant)', ln=True)

sender = ['Thomas Mueller', 'Hauptstrasse 42', '10115 Berlin', 'Tel: +49 30 12345678']
receiver = ['Herr Raj Kumar', 'Hauptstrasse 42, Wohnung 3B', '10115 Berlin', 'Mieter seit: 01.03.2024']
for s, r in zip(sender, receiver):
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 60, 75)
    pdf.cell(col_w, 6, s, ln=False)
    pdf.set_x(20 + col_w + 5)
    pdf.cell(col_w, 6, r, ln=True)

pdf.ln(4)
pdf.set_font('Helvetica', '', 10)
pdf.set_text_color(50, 60, 75)
pdf.cell(0, 6, 'Berlin, 20. Mai 2026', ln=True)
pdf.ln(2)
pdf.set_font('Helvetica', 'B', 11)
pdf.set_text_color(11, 31, 58)
pdf.cell(0, 7, 'Betreff: Abmahnung wegen Mietruckstand und Vertragsverstoss', ln=True)
pdf.ln(2)
divider(pdf)

body(pdf, 'Sehr geehrter Herr Kumar,\n\nIch schreibe Ihnen bezueglich mehrerer Verstosse gegen Ihren Mietvertrag vom 1. Maerz 2024 fuer die Wohnung in der Hauptstrasse 42, 3. Etage links (3B), 10115 Berlin.')

# Section 1
section_header(pdf, '  1.  MIETRUCKSTAND  (Rent Arrears)')
body(pdf, 'Ihre monatliche Miete betraegt gemaess Mietvertrag 1.200,00 Euro\n(Kaltmiete: 950,00 Euro + Nebenkosten: 250,00 Euro), zahlbar zum 3. Werktag eines jeden Monats.\n\nFolgende Mietzahlungen sind ausgeblieben:')

for month, amount, due in [
    ('Maerz 2026', '1.200,00 Euro', '03.03.2026'),
    ('April 2026', '1.200,00 Euro', '03.04.2026'),
    ('Mai   2026', '1.200,00 Euro', '03.05.2026'),
]:
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 60, 75)
    pdf.cell(10, 6, '')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(32, 6, '  ' + month + ':')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(42, 6, amount)
    pdf.cell(0, 6, '(faellig am ' + due + ')', ln=True)

pdf.ln(2)
highlight_box(pdf, '  GESAMTRUCKSTAND:', '  3.600,00 Euro', color=(255, 235, 210))
body(pdf, 'Trotz muendlicher Aufforderung meinerseits am 15. April 2026 haben Sie die ausstehenden Betraege nicht beglichen.')

# Section 2
section_header(pdf, '  2.  VERSTOSS GEGEN DIE HAUSORDNUNG  (House Rules Violation)')
body(pdf, 'Mehrere Mitbewohner haben Beschwerden ueber naechtliche Ruhestoerungen eingereicht. Am 5. April 2026 und 18. April 2026 wurde durch laute Musik nach 22:00 Uhr die Nachtruhe erheblich gestoert.\n\nDies stellt einen Verstoss gegen SS 4 des Mietvertrages sowie gegen die Hausordnung dar.')

# Section 3
section_header(pdf, '  3.  UNERLAUBTE UNTERVERMIETUNG  (Illegal Subletting)')
body(pdf, 'Es ist mir zur Kenntnis gelangt, dass Sie seit Februar 2026 Teile der Wohnung ohne meine schriftliche Genehmigung untervermieten. Dies stellt einen schwerwiegenden Verstoss gegen SS 7 Abs. 2 des Mietvertrages dar und ist gemaess SS 540 BGB ohne Erlaubnis des Vermieters unzulaessig.')

# Demands
section_header(pdf, '  AUFFORDERUNG ZUR ABHILFE  (Demands)')
body(pdf, 'Ich fordere Sie hiermit auf:')
demands = [
    '1.  Den gesamten Mietruckstand von 3.600,00 Euro bis 31. Mai 2026 zu ueberweisen:\n    IBAN: DE12 1234 5678 9012 3456 78  |  BIC: BELADEBEXXX',
    '2.  Die unerlaubte Untervermietung sofort einzustellen und dies schriftlich zu bestaetigen.',
    '3.  Weitere Verstoesse gegen die Hausordnung zu unterlassen.',
]
for d in demands:
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 60, 75)
    pdf.cell(8, 6, '')
    pdf.multi_cell(0, 6, d)
    pdf.ln(1)

# Consequences
section_header(pdf, '  RECHTLICHE KONSEQUENZEN  (Legal Consequences)')
consequences = [
    'Ausserordentliche fristlose Kuendigung gem. SS 543 Abs. 2 Nr. 3 BGB.',
    'Gerichtliche Raeumungsklage sowie Zahlungsklage auf ausstehende Mieten.',
    'Schadensersatzansprueche wegen unerlaubter Untervermietung.',
]
for c in consequences:
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 60, 75)
    pdf.cell(8, 6, '')
    pdf.cell(5, 6, '-')
    pdf.multi_cell(0, 6, c)
    pdf.ln(1)

# Closing
divider(pdf)
body(pdf, 'Ich bin weiterhin zu einer einvernehmlichen Loesung bereit, erwarte jedoch umgehend eine schriftliche Stellungnahme sowie die Zahlung des Rueckstands.')
pdf.ln(4)
pdf.set_font('Helvetica', '', 10)
pdf.set_text_color(50, 60, 75)
pdf.cell(0, 6, 'Mit freundlichen Gruessen,', ln=True)
pdf.ln(8)
pdf.set_font('Helvetica', 'B', 10)
pdf.set_text_color(11, 31, 58)
pdf.cell(0, 6, 'Thomas Mueller  (Eigentuemer und Vermieter)', ln=True)
pdf.ln(4)
pdf.set_font('Helvetica', 'I', 9)
pdf.set_text_color(100, 120, 150)
pdf.cell(0, 6, 'Anlage: Kopie Mietvertrag, Kontoauszuege (Maerz-Mai 2026), Beschwerdeprotokolle', ln=True)

# Warning box
pdf.ln(4)
pdf.set_fill_color(254, 242, 242)
pdf.set_draw_color(239, 68, 68)
pdf.set_line_width(0.5)
pdf.set_font('Helvetica', 'B', 9)
pdf.set_text_color(185, 28, 28)
pdf.multi_cell(0, 7, '  HINWEIS: Dieses Schreiben ist ein rechtliches Dokument. Es wird dringend empfohlen, umgehend anwaltlichen Beistand zu suchen.', border=1, fill=True)

outpath = r'C:\Users\sriva\Desktop\Projects\Personal Repositories\AdvocateAI\sample_legal_document.pdf'
pdf.output(outpath)
print('PDF saved to Desktop/Projects/AdvocateAI/sample_legal_document.pdf')
