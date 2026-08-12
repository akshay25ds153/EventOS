import os
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_ticket_qr(ticket):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(ticket.uuid))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    filename = f"qr_{ticket.ticket_number}.png"
    ticket.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)

def generate_ticket_pdf(ticket):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=15
    )
    
    text_bold = ParagraphStyle(
        'TextBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4
    )
    
    text_normal = ParagraphStyle(
        'TextNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=4
    )

    story = []
    
    # Header Banner
    if ticket.event.banner:
        try:
            banner_path = ticket.event.banner.path
            banner_img = Image(banner_path, width=7*inch, height=2*inch)
            story.append(banner_img)
            story.append(Spacer(1, 15))
        except Exception:
            pass
            
    # Title
    story.append(Paragraph(ticket.event.name, title_style))
    story.append(Spacer(1, 10))
    
    # Ticket info grid
    # Left: Details, Right: QR Code
    details_data = [
        [Paragraph("Attendee Name:", text_normal), Paragraph(ticket.member.name, text_bold)],
        [Paragraph("Reg Number:", text_normal), Paragraph(ticket.member.registration_number or "N/A", text_bold)],
        [Paragraph("Ticket ID:", text_normal), Paragraph(ticket.ticket_number, text_bold)],
        [Paragraph("Venue:", text_normal), Paragraph(ticket.event.venue.name if ticket.event.venue else "TBD", text_bold)],
        [Paragraph("Date:", text_normal), Paragraph(f"{ticket.event.start_date} to {ticket.event.end_date}", text_bold)],
        [Paragraph("Time:", text_normal), Paragraph(f"{ticket.event.start_time} - {ticket.event.end_time}", text_bold)],
    ]
    
    details_table = Table(details_data, colWidths=[1.5*inch, 2.5*inch])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    
    # QR Image
    qr_img = None
    if ticket.qr_code:
        try:
            qr_path = ticket.qr_code.path
            qr_img = Image(qr_path, width=2*inch, height=2*inch)
        except Exception:
            pass
            
    # layout table
    if qr_img:
        layout_data = [[details_table, qr_img]]
        layout_table = Table(layout_data, colWidths=[4*inch, 3*inch])
    else:
        layout_data = [[details_table]]
        layout_table = Table(layout_data, colWidths=[7*inch])
        
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    
    story.append(layout_table)
    story.append(Spacer(1, 30))
    
    # Divider line
    story.append(Table([[""]], colWidths=[7*inch], rowHeights=[1], style=[
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
    ]))
    story.append(Spacer(1, 15))
    
    # Organizer / Instructions
    story.append(Paragraph("Instructions:", text_bold))
    story.append(Paragraph("1. Please present this ticket at the check-in desk for verification.", text_normal))
    story.append(Paragraph("2. The QR Code is unique and can only be scanned once for entry.", text_normal))
    story.append(Paragraph("3. If you have any issues, contact the organizers or support team.", text_normal))
    
    doc.build(story)
    
    filename = f"ticket_{ticket.ticket_number}.pdf"
    ticket.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=False)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#64748B')) # Slate-500
        
        # Positions footer at 36 points from bottom (0.5 inch margin)
        width, height = self._pagesize
        
        # Draw header (top)
        self.setStrokeColor(colors.HexColor('#E2E8F0')) # Slate-200
        self.setLineWidth(0.5)
        self.line(36, height - 36 - 12, width - 36, height - 36 - 12)
        self.drawString(36, height - 36, "EventOS Automated Reporting Console")
        self.drawRightString(width - 36, height - 36, timezone.now().strftime('%d %b %Y'))
        
        # Draw footer (bottom)
        self.line(36, 36 + 12, width - 36, 36 + 12)
        self.drawString(36, 36, "EventOS — Confidential Report")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(width - 36, 36, page_text)
        
        self.restoreState()


def generate_pdf_report(title, headers, data, col_widths=None, landscape_mode=False, user="System", total_records=0):
    buffer = BytesIO()
    pagesize = landscape(letter) if landscape_mode else letter
    margin = 36 # 0.5 inch
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=pagesize, 
        rightMargin=margin, 
        leftMargin=margin, 
        topMargin=margin, 
        bottomMargin=margin + 20 # Leave space for the line/footer
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0F172A'), # Slate-900
        spaceAfter=8
    )
    
    meta_style = ParagraphStyle(
        'ReportMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#64748B'), # Slate-500
        spaceAfter=15
    )
    
    header_text_style = ParagraphStyle(
        'HeaderTextStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )
    
    cell_text_style = ParagraphStyle(
        'CellTextStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#334155') # Slate-700
    )
    
    no_records_style = ParagraphStyle(
        'NoRecordsStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.HexColor('#DC2626'), # Red-600
        spaceBefore=30,
        spaceAfter=30,
        alignment=1 # Center
    )
    
    story = []
    
    # Metadata for ReportLab Document Properties
    doc.author = "EventOS System"
    doc.title = title
    doc.subject = f"EventOS Automated Report: {title}"
    doc.keywords = "EventOS, Report, Export"
    
    # Add title
    story.append(Paragraph(title, title_style))
    
    # Add metadata (date generated)
    now_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    story.append(Paragraph(f"Generated on: {now_str} | Generated By: {user} | Total Records: {total_records}", meta_style))
    
    if total_records == 0:
        story.append(Paragraph("No records matched the active search filters.", no_records_style))
    else:
        # Process headers
        p_headers = [Paragraph(h, header_text_style) for h in headers]
        
        # Process data rows
        p_data = []
        p_data.append(p_headers)
        for row in data:
            p_row = [Paragraph(str(cell) if cell is not None else "", cell_text_style) for cell in row]
            p_data.append(p_row)
            
        printable_width = 720 if landscape_mode else 540
        
        if not col_widths:
            num_cols = len(headers)
            col_widths = [printable_width / num_cols] * num_cols
        else:
            total_custom_width = sum(col_widths)
            scale = printable_width / total_custom_width
            col_widths = [w * scale for w in col_widths]
            
        table = Table(p_data, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')), # Dark slate header
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), # Slate-200 grid borders
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        
        story.append(table)
        
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
