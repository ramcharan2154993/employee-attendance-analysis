"""Script to generate a professional 10-slide PowerPoint presentation for AttendIQ.

Tailored for College Faculty evaluation, Batch 4.
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# Output presentation file
OUTPUT_FILE = Path("AttendIQ_Presentation.pptx")
CHARTS_DIR = Path("output")

# Color Palette (Derived from AttendIQ design system)
COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900 (#0F172A)
COLOR_SURFACE_DARK = RGBColor(30, 41, 59)   # Slate 800 (#1E293B)
COLOR_CARD_BORDER = RGBColor(51, 65, 85)    # Slate 700 (#334155)

COLOR_BG_LIGHT = RGBColor(248, 250, 252)    # Slate 50 (#F8FAFC)
COLOR_SURFACE_LIGHT = RGBColor(255, 255, 255) # Pure White
COLOR_BORDER_LIGHT = RGBColor(226, 232, 240) # Slate 200 (#E2E8F0)

COLOR_PRIMARY = RGBColor(37, 99, 235)       # Royal Blue (#2563EB)
COLOR_PRIMARY_LIGHT = RGBColor(59, 130, 246)# Accent Blue (#3B82F6)
COLOR_PRIMARY_SUBTLE = RGBColor(239, 246, 255) # Ice Blue (#EFF6FF)

COLOR_TEXT_WHITE = RGBColor(248, 250, 252)  # #F8FAFC
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400 (#94A3B8)
COLOR_TEXT_DARK = RGBColor(15, 23, 42)      # Slate 900 (#0F172A)
COLOR_TEXT_BODY = RGBColor(51, 65, 85)      # Slate 700 (#334155)

COLOR_EMERALD = RGBColor(16, 185, 129)      # Present (#10B981)
COLOR_ROSE = RGBColor(239, 68, 68)          # Absent (#EF4444)
COLOR_AMBER = RGBColor(245, 158, 11)        # Leave (#F59E0B)
COLOR_PURPLE = RGBColor(139, 92, 246)       # Holiday (#8B5CF6)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"


def set_slide_background(slide, color: RGBColor) -> None:
    """Set solid background color for a slide."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(
    slide,
    category: str,
    title: str,
    subtitle: str | None = None,
    is_dark: bool = True,
) -> None:
    """Add a consistent, beautifully styled header to the slide."""
    # Category badge / kicker
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.name = FONT_HEADING
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_PRIMARY_LIGHT if is_dark else COLOR_PRIMARY

    # Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.65))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(28)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_WHITE if is_dark else COLOR_TEXT_DARK

    # Optional Subtitle / Tagline
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(11.7), Inches(0.4))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        tf_sub.margin_left = tf_sub.margin_right = tf_sub.margin_top = tf_sub.margin_bottom = 0
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(14)
        p_sub.font.color.rgb = COLOR_TEXT_MUTED if is_dark else COLOR_TEXT_BODY


def add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    bg_color: RGBColor = COLOR_SURFACE_DARK,
    border_color: RGBColor = COLOR_CARD_BORDER,
    border_width: float = 1.0,
):
    """Add a card container rectangle shape."""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(border_width)
    return card


def add_screenshot_placeholder(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    label: str,
    instructions: str = "Upload screenshot to replace this placeholder",
    is_dark: bool = True,
):
    """Create a clean, labeled screenshot placeholder box."""
    # Outer box
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(24, 32, 47) if is_dark else RGBColor(241, 245, 249)
    box.line.color.rgb = COLOR_PRIMARY_LIGHT if is_dark else COLOR_PRIMARY
    box.line.width = Pt(1.5)

    # Inner Text & instructions
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    p1.text = "📷 SCREENSHOT PLACEHOLDER"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_PRIMARY_LIGHT if is_dark else COLOR_PRIMARY

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = label
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(15)
    p2.font.bold = True
    p2.font.color.rgb = COLOR_TEXT_WHITE if is_dark else COLOR_TEXT_DARK

    p3 = tf.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = instructions
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = COLOR_TEXT_MUTED if is_dark else COLOR_TEXT_BODY


def set_speaker_notes(slide, notes_text: str) -> None:
    """Attach concise 3 to 4 sentence speaker notes to the slide."""
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = notes_text.strip()


def build_presentation() -> Presentation:
    """Build the complete 10-slide PowerPoint presentation."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, COLOR_BG_DARK)

    # Ambient Accent Glow bar on left
    accent_bar = s1.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.12), Inches(3.8)
    )
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = COLOR_PRIMARY
    accent_bar.line.fill.background()

    # Kicker Badge
    kicker = s1.shapes.add_textbox(Inches(1.1), Inches(1.5), Inches(10.0), Inches(0.4))
    tf_k = kicker.text_frame
    p_k = tf_k.paragraphs[0]
    p_k.text = "ACADEMIC CAPSTONE PROJECT EVALUATION  •  BATCH 4"
    p_k.font.name = FONT_HEADING
    p_k.font.size = Pt(12)
    p_k.font.bold = True
    p_k.font.color.rgb = COLOR_PRIMARY_LIGHT

    # Main Project Title
    title_box = s1.shapes.add_textbox(Inches(1.1), Inches(1.85), Inches(11.0), Inches(1.2))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = "AttendIQ"
    p_t.font.name = FONT_HEADING
    p_t.font.size = Pt(48)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_TEXT_WHITE

    # Subtitle
    sub_box = s1.shapes.add_textbox(Inches(1.1), Inches(3.0), Inches(11.0), Inches(0.8))
    tf_s = sub_box.text_frame
    tf_s.word_wrap = True
    p_s = tf_s.paragraphs[0]
    p_s.text = "Enterprise Human Resources Attendance Tracking & Absenteeism Intelligence System"
    p_s.font.name = FONT_HEADING
    p_s.font.size = Pt(20)
    p_s.font.color.rgb = COLOR_PRIMARY_LIGHT

    # Description
    desc_box = s1.shapes.add_textbox(Inches(1.1), Inches(3.7), Inches(10.8), Inches(0.7))
    tf_d = desc_box.text_frame
    tf_d.word_wrap = True
    p_d = tf_d.paragraphs[0]
    p_d.text = (
        "A mathematically rigorous, dual-interface software platform solving the Averaging Trap, "
        "enforcing atomic batch transactions, and providing automated cohort intelligence."
    )
    p_d.font.name = FONT_BODY
    p_d.font.size = Pt(14)
    p_d.font.color.rgb = COLOR_TEXT_MUTED

    # Team & Presentation Info Card
    add_card(s1, 1.1, 4.7, 11.2, 2.0, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)

    card_box = s1.shapes.add_textbox(Inches(1.4), Inches(4.85), Inches(10.6), Inches(1.7))
    tf_c = card_box.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0

    p_c1 = tf_c.paragraphs[0]
    p_c1.text = "PROJECT TEAM MEMBERS (BATCH 4)"
    p_c1.font.name = FONT_HEADING
    p_c1.font.size = Pt(11)
    p_c1.font.bold = True
    p_c1.font.color.rgb = COLOR_PRIMARY_LIGHT

    p_c2 = tf_c.add_paragraph()
    p_c2.space_before = Pt(4)
    p_c2.text = "1) V. Ramcharan Reddy (Lead)    2) Nikhil    3) Adarsh    4) Surekha    5) Madhavi"
    p_c2.font.name = FONT_HEADING
    p_c2.font.size = Pt(16)
    p_c2.font.bold = True
    p_c2.font.color.rgb = COLOR_TEXT_WHITE

    p_c3 = tf_c.add_paragraph()
    p_c3.space_before = Pt(8)
    p_c3.text = "Target Audience: College Faculty & Academic Examiners  |  Framework: Python 3.14 · Flask · MySQL · Pandas · Matplotlib  |  186 Tests Passing"
    p_c3.font.name = FONT_BODY
    p_c3.font.size = Pt(12)
    p_c3.font.color.rgb = COLOR_TEXT_MUTED

    set_speaker_notes(
        s1,
        "Respected faculty members and examiners, good morning. We are Team Batch Four—Ramcharan, Nikhil, Adarsh, "
        "Surekha, and Madhavi—and we are pleased to present AttendIQ, our enterprise attendance tracking and absenteeism intelligence system. "
        "This project was engineered to solve foundational mathematical distortion and transactional failures present in standard HR tracking systems. "
        "Across the next eight minutes, we will walk you through the system architecture, mathematical formulas, core features, and test-driven verification."
    )

    # =========================================================================
    # SLIDE 2: Problem Statement & Academic Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, COLOR_BG_DARK)
    add_header(
        s2,
        "Problem Statement & Motivation",
        "Critical Flaws in Conventional Attendance Tracking",
        "Why naive spreadsheet trackers and basic CRUD database scripts fail in enterprise environments",
    )

    cards_data = [
        (
            "1. The Averaging Trap",
            "Computing cohort attendance by averaging employee percentages creates massive mathematical distortion. A worker with 1 day is falsely given the exact same weight as someone with 22 days.",
            COLOR_ROSE,
        ),
        (
            "2. Conflating Leave with Absence",
            "Naive systems treat authorized medical/annual leave as unexcused absenteeism, unfairly penalizing compliant staff, or omit it from scheduled working days, artificially inflating rates.",
            COLOR_AMBER,
        ),
        (
            "3. Partial Batch Inconsistencies",
            "When submitting department-wide attendance, partial failures or unhandled duplicate record insertions leave the database in an inconsistent, corrupt state without rollback safety.",
            COLOR_PRIMARY_LIGHT,
        ),
        (
            "4. Audit Trail Destruction",
            "Hard SQL deletes destroy historical compliance baselines. Furthermore, recording attendance on dates prior to employment commencement corrupts historical company analytics.",
            COLOR_PURPLE,
        ),
    ]

    card_w = 5.6
    card_h = 2.2
    positions = [
        (0.8, 2.0),
        (6.9, 2.0),
        (0.8, 4.5),
        (6.9, 4.5),
    ]

    for (title, text, badge_color), (cx, cy) in zip(cards_data, positions):
        add_card(s2, cx, cy, card_w, card_h, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)

        # Content in card
        cbox = s2.shapes.add_textbox(Inches(cx + 0.3), Inches(cy + 0.25), Inches(card_w - 0.6), Inches(card_h - 0.5))
        tf = cbox.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(17)
        p1.font.bold = True
        p1.font.color.rgb = badge_color

        p2 = tf.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = text
        p2.font.name = FONT_BODY
        p2.font.size = Pt(13)
        p2.font.color.rgb = COLOR_TEXT_WHITE

    set_speaker_notes(
        s2,
        "In our research, we identified four structural flaws across traditional academic and corporate attendance systems. "
        "The most widespread flaw is 'The Averaging Trap': managers calculate department attendance by averaging individual percentages, mathematically distorting figures. "
        "Secondly, approved medical and annual leave are routinely conflated with unauthorized absenteeism. "
        "Finally, naive systems lack transactional rollback during bulk department updates and destroy audit trails through hard record deletions. AttendIQ systematically solves each of these vulnerabilities."
    )

    # =========================================================================
    # SLIDE 3: System Solution & Mathematical Foundations
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, COLOR_BG_DARK)
    add_header(
        s3,
        "System Solution & Mathematical Foundations",
        "Authoritative Business Rules & Aggregate Cohort Principles",
        "Decoupled, pure mathematical formulas implemented in calculations.py with zero division errors",
    )

    # Left Column: Mathematical Formulas Card
    add_card(s3, 0.8, 1.9, 5.8, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    lbox = s3.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.2), Inches(4.4))
    tf_l = lbox.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_right = tf_l.margin_top = tf_l.margin_bottom = 0

    p_f1 = tf_l.paragraphs[0]
    p_f1.text = "CORE MATHEMATICAL FORMULATIONS"
    p_f1.font.name = FONT_HEADING
    p_f1.font.size = Pt(15)
    p_f1.font.bold = True
    p_f1.font.color.rgb = COLOR_PRIMARY_LIGHT

    formulas = [
        (
            "Eligible Working Days (The Denominator):",
            "Eligible Days = Present + Absent + Leave\n(Public Holiday rows are strictly excluded)",
            COLOR_TEXT_WHITE,
        ),
        (
            "Individual Attendance & Absenteeism Rates:",
            "Attendance % = (Present / Eligible Days) × 100\nAbsenteeism % = (Absent / Eligible Days) × 100\n(Approved Leave is authorized; never counts as absence)",
            COLOR_TEXT_WHITE,
        ),
        (
            "The Zero-Eligible-Days Invariant ('N/A'):",
            "If Eligible Days = 0, division by zero is safely trapped. Raw function returns None; UI renders 'N/A' (never 0.00%).",
            COLOR_EMERALD,
        ),
    ]

    for title, formula_text, col in formulas:
        p_t = tf_l.add_paragraph()
        p_t.space_before = Pt(12)
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_AMBER

        p_b = tf_l.add_paragraph()
        p_b.space_before = Pt(2)
        p_b.text = formula_text
        p_b.font.name = FONT_BODY
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = col

    # Right Column: The Averaging Trap Numerical Proof Card
    add_card(s3, 6.9, 1.9, 5.6, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    rbox = s3.shapes.add_textbox(Inches(7.2), Inches(2.1), Inches(5.0), Inches(4.4))
    tf_r = rbox.text_frame
    tf_r.word_wrap = True
    tf_r.margin_left = tf_r.margin_right = tf_r.margin_top = tf_r.margin_bottom = 0

    p_r1 = tf_r.paragraphs[0]
    p_r1.text = "NUMERICAL PROOF: THE AVERAGING TRAP"
    p_r1.font.name = FONT_HEADING
    p_r1.font.size = Pt(15)
    p_r1.font.bold = True
    p_r1.font.color.rgb = COLOR_ROSE

    p_r2 = tf_r.add_paragraph()
    p_r2.space_before = Pt(8)
    p_r2.text = (
        "Scenario: Engineering team of 2 employees:\n"
        "• Employee E001: 1 Present / 2 Scheduled Days (50.00%)\n"
        "• Employee E002: 1 Present / 1 Scheduled Day (100.00%)"
    )
    p_r2.font.name = FONT_BODY
    p_r2.font.size = Pt(13)
    p_r2.font.color.rgb = COLOR_TEXT_MUTED

    p_r3 = tf_r.add_paragraph()
    p_r3.space_before = Pt(12)
    p_r3.text = "❌ Naive Average of Percentages:"
    p_r3.font.name = FONT_HEADING
    p_r3.font.size = Pt(14)
    p_r3.font.bold = True
    p_r3.font.color.rgb = COLOR_ROSE

    p_r4 = tf_r.add_paragraph()
    p_r4.space_before = Pt(2)
    p_r4.text = "(50.00% + 100.00%) / 2 = 75.00%  [DISTORTED]"
    p_r4.font.name = FONT_BODY
    p_r4.font.size = Pt(14)
    p_r4.font.bold = True
    p_r4.font.color.rgb = COLOR_TEXT_WHITE

    p_r5 = tf_r.add_paragraph()
    p_r5.space_before = Pt(14)
    p_r5.text = "✓ AttendIQ Aggregate Sum of Days (Strict Standard):"
    p_r5.font.name = FONT_HEADING
    p_r5.font.size = Pt(14)
    p_r5.font.bold = True
    p_r5.font.color.rgb = COLOR_EMERALD

    p_r6 = tf_r.add_paragraph()
    p_r6.space_before = Pt(2)
    p_r6.text = (
        "Total Present = 1 + 1 = 2 days\n"
        "Total Eligible = 2 + 1 = 3 days\n"
        "Dept Rate = (2 / 3) × 100 = 66.67%  [MATHEMATICALLY ACCURATE]"
    )
    p_r6.font.name = FONT_BODY
    p_r6.font.size = Pt(13)
    p_r6.font.bold = True
    p_r6.font.color.rgb = COLOR_TEXT_WHITE

    set_speaker_notes(
        s3,
        "Here we see the mathematical core of AttendIQ, implemented cleanly in calculations.py. "
        "Eligible working days strictly exclude holidays, while counting approved leave without penalizing the employee's absenteeism rate. "
        "On the right card, we provide our mathematical proof of the Averaging Trap. If Employee A has 1 out of 2 days and Employee B has 1 out of 1 day, "
        "averaging their percentages yields an erroneous 75.00%. AttendIQ aggregates raw day counts first—2 days out of 3—yielding the true rate of 66.67%."
    )

    # =========================================================================
    # SLIDE 4: Technology Stack & Architectural Guardrails
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, COLOR_BG_DARK)
    add_header(
        s4,
        "Technology Stack & Invariants",
        "Modern Full-Stack Python Architecture",
        "Zero external JavaScript frameworks; strictly decoupled with verified architectural constraints",
    )

    tech_cards = [
        (
            "Frontend & UI Design",
            [
                "Semantic HTML5 & Vanilla CSS (Dark Slate + Royal Blue).",
                "Self-hosted Inter & Plus Jakarta Sans typography.",
                "Accessible HTML5 native datalists (zero JS injection risk).",
                "Full Content-Security-Policy (CSP) compliance.",
            ],
            COLOR_PRIMARY_LIGHT,
        ),
        (
            "Backend & Routing",
            [
                "Python 3.14.6 core language and business logic runtime.",
                "Flask 3.1.3 WSGI web framework & Jinja2 templating.",
                "Dual Presentation: Web App + 15-option Terminal CLI.",
                "Session authentication & Werkzeug password hashing.",
            ],
            COLOR_EMERALD,
        ),
        (
            "Database & Storage",
            [
                "MySQL Server 8.0+ running the InnoDB ACID engine.",
                "mysql-connector-python 26.7.0 driver with 100% parameterized SQL.",
                "Foreign Key ON DELETE RESTRICT (prohibits employee row deletion).",
                "Composite Unique Key uq_employee_date prevents duplicate days.",
            ],
            COLOR_AMBER,
        ),
        (
            "Analytics & Testing",
            [
                "Pandas 3.0.6: In-memory DataFrames, GroupBy & aggregations.",
                "NumPy 2.5.4: High-performance vectorized percentage calculations.",
                "Matplotlib 3.11.2: Headless (Agg) chart generation to PNG.",
                "pytest 9.1.1: 186 automated unit, integration, and security tests.",
            ],
            COLOR_PURPLE,
        ),
    ]

    card_w = 5.6
    card_h = 2.25
    positions = [
        (0.8, 1.95),
        (6.9, 1.95),
        (0.8, 4.45),
        (6.9, 4.45),
    ]

    for (title, bullets, accent_col), (cx, cy) in zip(tech_cards, positions):
        add_card(s4, cx, cy, card_w, card_h, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)

        tbox = s4.shapes.add_textbox(Inches(cx + 0.3), Inches(cy + 0.2), Inches(card_w - 0.6), Inches(card_h - 0.4))
        tf = tbox.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = accent_col

        for b in bullets:
            pb = tf.add_paragraph()
            pb.space_before = Pt(4)
            pb.text = f"• {b}"
            pb.font.name = FONT_BODY
            pb.font.size = Pt(12)
            pb.font.color.rgb = COLOR_TEXT_WHITE

    set_speaker_notes(
        s4,
        "Our technology stack was carefully selected to prioritize security, mathematical accuracy, and maintainability. "
        "The frontend uses semantic HTML5 and vanilla CSS with zero heavy JavaScript frameworks, ensuring complete Content Security Policy compliance. "
        "The backend is powered by Python 3.14 and Flask, connecting to MySQL 8.0 on the InnoDB engine using 100% parameterized queries. "
        "For analytical processing, we leverage Pandas and NumPy for in-memory vector calculations, while Matplotlib generates headless report charts. Every layer is verified by 186 automated pytest tests."
    )

    # =========================================================================
    # SLIDE 5: System Architecture & Three-Tier Layering
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, COLOR_BG_DARK)
    add_header(
        s5,
        "System Architecture",
        "Decoupled Three-Tier Architectural Design",
        "Rigorous separation of presentation, transactional business logic, analytics, and persistent storage",
    )

    # Tier 1: Presentation Layer
    add_card(s5, 0.8, 1.95, 11.7, 1.25, COLOR_SURFACE_DARK, COLOR_PRIMARY)
    p_box = s5.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(11.3), Inches(1.05))
    tf_p = p_box.text_frame
    tf_p.word_wrap = True
    tf_p.margin_left = tf_p.margin_right = tf_p.margin_top = tf_p.margin_bottom = 0
    p1 = tf_p.paragraphs[0]
    p1.text = "1. PRESENTATION TIER (DUAL INTERFACES — ZERO SQL & ZERO FORMULAS)"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(14)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_PRIMARY_LIGHT

    p2 = tf_p.add_paragraph()
    p2.space_before = Pt(3)
    p2.text = (
        "• Flask Web Application: routes.py & write_routes.py | Jinja2 Templates (Dark Slate) | Anti-CSRF Token Validation\n"
        "• Interactive Console CLI: src/main.py (15 standalone terminal operations with keyboard input validation and traps)"
    )
    p2.font.name = FONT_BODY
    p2.font.size = Pt(12)
    p2.font.color.rgb = COLOR_TEXT_WHITE

    # Connector Arrow 1
    arrow1 = s5.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(6.4), Inches(3.25), Inches(0.5), Inches(0.25))
    arrow1.fill.solid()
    arrow1.fill.fore_color.rgb = COLOR_PRIMARY_LIGHT
    arrow1.line.fill.background()

    # Tier 2: Business & Analytics Layer
    add_card(s5, 0.8, 3.55, 11.7, 1.5, COLOR_SURFACE_DARK, COLOR_EMERALD)
    b_box = s5.shapes.add_textbox(Inches(1.0), Inches(3.65), Inches(11.3), Inches(1.3))
    tf_b = b_box.text_frame
    tf_b.word_wrap = True
    tf_b.margin_left = tf_b.margin_right = tf_b.margin_top = tf_b.margin_bottom = 0
    pb1 = tf_b.paragraphs[0]
    pb1.text = "2. BUSINESS LOGIC & ANALYTICAL PROCESSING TIER"
    pb1.font.name = FONT_HEADING
    pb1.font.size = Pt(14)
    pb1.font.bold = True
    pb1.font.color.rgb = COLOR_EMERALD

    pb2 = tf_b.add_paragraph()
    pb2.space_before = Pt(3)
    pb2.text = (
        "• Domain Logic: employees.py (CRUD, joining date constraints) | attendance.py (atomic batch, weekend checks, holidays)\n"
        "• Pure Calculations: calculations.py (raw float formulas, eligible days denominator, zero-day 'N/A' safe formatting)\n"
        "• Analytics & Charts: analysis.py (SQL-to-DataFrame, cohort summaries) | visualizations.py (headless Matplotlib charts)"
    )
    pb2.font.name = FONT_BODY
    pb2.font.size = Pt(12)
    pb2.font.color.rgb = COLOR_TEXT_WHITE

    # Connector Arrow 2
    arrow2 = s5.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(6.4), Inches(5.1), Inches(0.5), Inches(0.25))
    arrow2.fill.solid()
    arrow2.fill.fore_color.rgb = COLOR_EMERALD
    arrow2.line.fill.background()

    # Tier 3: Database & Storage Layer
    add_card(s5, 0.8, 5.4, 11.7, 1.4, COLOR_SURFACE_DARK, COLOR_AMBER)
    d_box = s5.shapes.add_textbox(Inches(1.0), Inches(5.5), Inches(11.3), Inches(1.2))
    tf_d = d_box.text_frame
    tf_d.word_wrap = True
    tf_d.margin_left = tf_d.margin_right = tf_d.margin_top = tf_d.margin_bottom = 0
    pd1 = tf_d.paragraphs[0]
    pd1.text = "3. DATABASE & PERSISTENCE TIER (ACID COMPLIANT & ISOLATED)"
    pd1.font.name = FONT_HEADING
    pd1.font.size = Pt(14)
    pd1.font.bold = True
    pd1.font.color.rgb = COLOR_AMBER

    pd2 = tf_d.add_paragraph()
    pd2.space_before = Pt(3)
    pd2.text = (
        "• Database Engine: MySQL 8.0+ InnoDB | Connection factory & schema migration engine (src/db.py)\n"
        "• Tables: employees (Indexed code, joining_date, is_active) | attendance (Composite UNIQUE uq_employee_date, FK RESTRICT)\n"
        "• Governance & Security: users table (role ENUM, password_hash) | attendance_audit table (immutable action history)"
    )
    pd2.font.name = FONT_BODY
    pd2.font.size = Pt(12)
    pd2.font.color.rgb = COLOR_TEXT_WHITE

    set_speaker_notes(
        s5,
        "This diagram illustrates the three-tier architectural layout of AttendIQ. "
        "At the top tier, our web application and interactive CLI operate in parallel, completely decoupled from SQL queries or calculation formulas. "
        "The middle tier coordinates business rules—such as weekend validations and atomic bulk batching—while Pandas and NumPy handle data aggregation. "
        "At the bottom tier, MySQL InnoDB enforces referential integrity through foreign keys with ON DELETE RESTRICT and composite unique constraints, backed by an immutable audit table."
    )

    # =========================================================================
    # SLIDE 6: End-to-End User Flow & Department Batch Processing
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, COLOR_BG_DARK)
    add_header(
        s6,
        "System Workflow",
        "End-to-End User Flow & Atomic Transaction Lifecycle",
        "Step-by-step request progression from authentication to atomic database commit",
    )

    steps_data = [
        ("Step 1: Ingress & Auth", "User submits credentials on /login. Evaluated by Dual-Cap Rate Limiter (max 5 fails/10m). Signed session initialized.", COLOR_PRIMARY_LIGHT),
        ("Step 2: RBAC Evaluation", "Middleware checks user role (Admin vs HR). Admin grants user provisioning; HR grants operational logging.", COLOR_PRIMARY_LIGHT),
        ("Step 3: Roster Query", "Operator selects Department + Date on /attendance/department. Queries active staff joined on or before date.", COLOR_AMBER),
        ("Step 4: Conflict Check", "System performs pre-insert conflict query. If any staff member already has attendance, an alert warning blocks entry.", COLOR_AMBER),
        ("Step 5: Atomic Batch", "Transaction starts (autocommit=False). Inserts all records via executemany(). If 1 fails, entire batch is rolled back.", COLOR_EMERALD),
        ("Step 6: Audit & Analytics", "Appends action to attendance_audit. Pandas recalculates cohort metrics. Output rendered with updated KPI cards.", COLOR_PURPLE),
    ]

    sw = 3.65
    sh = 2.2
    spos = [
        (0.8, 1.95), (4.8, 1.95), (8.8, 1.95),
        (0.8, 4.45), (4.8, 4.45), (8.8, 4.45),
    ]

    for (stitle, sdesc, scol), (sx, sy) in zip(steps_data, spos):
        add_card(s6, sx, sy, sw, sh, COLOR_SURFACE_DARK, scol, border_width=1.5)
        sbox = s6.shapes.add_textbox(Inches(sx + 0.25), Inches(sy + 0.2), Inches(sw - 0.5), Inches(sh - 0.4))
        tf_s = sbox.text_frame
        tf_s.word_wrap = True
        tf_s.margin_left = tf_s.margin_right = tf_s.margin_top = tf_s.margin_bottom = 0

        p1 = tf_s.paragraphs[0]
        p1.text = stitle
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = scol

        p2 = tf_s.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = sdesc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_TEXT_WHITE

    set_speaker_notes(
        s6,
        "Here we trace the complete end-to-end user workflow during department attendance recording. "
        "The operator signs in through our rate-limited login gateway, where their role is validated. "
        "Upon choosing a department and date, AttendIQ queries eligible staff while filtering out employees who have not yet reached their joining date. "
        "A pre-submission query checks for duplicate entries; if clean, the batch executes atomically inside a single database transaction with automatic rollback protection."
    )

    # =========================================================================
    # SLIDE 7: Core Feature: Department Bulk Attendance
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, COLOR_BG_DARK)
    add_header(
        s7,
        "Core Feature Spotlight",
        "Department Bulk Attendance & Atomic Transactions",
        "Fast batch entry with collision detection and automated transactional rollback",
    )

    # Left: Details Card
    add_card(s7, 0.8, 1.95, 5.8, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    fbox = s7.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.2), Inches(4.4))
    tf_f = fbox.text_frame
    tf_f.word_wrap = True
    tf_f.margin_left = tf_f.margin_right = tf_f.margin_top = tf_f.margin_bottom = 0

    p_f1 = tf_f.paragraphs[0]
    p_f1.text = "TRANSACTIONAL BULK ROSTER CAPABILITIES"
    p_f1.font.name = FONT_HEADING
    p_f1.font.size = Pt(15)
    p_f1.font.bold = True
    p_f1.font.color.rgb = COLOR_PRIMARY_LIGHT

    f_bullets = [
        ("Dynamic Active Roster", "Loads all active department staff whose joining_date is on or before selected date. Inactive staff are automatically excluded."),
        ("Pre-Submission Conflict Alert", "Detects existing records on the chosen date, alerting the operator with conflicting codes before database submission."),
        ("One-Click Productivity", "Defaults all roster staff to 'Present' with a one-click reset button and individual radio toggles (Present / Absent / Leave)."),
        ("Atomic Rollback Guarantee", "conn.autocommit = False wraps cursor.executemany(). Any MySQL error 1062 triggers immediate rollback—zero partial writes."),
        ("Weekend & Date Safeguards", "Rejects attendance on Saturdays and Sundays (weekday >= 5) and validates ISO date formats."),
    ]

    for b_title, b_desc in f_bullets:
        pb_t = tf_f.add_paragraph()
        pb_t.space_before = Pt(8)
        pb_t.text = f"• {b_title}:"
        pb_t.font.name = FONT_HEADING
        pb_t.font.size = Pt(13)
        pb_t.font.bold = True
        pb_t.font.color.rgb = COLOR_AMBER

        pb_d = tf_f.add_paragraph()
        pb_d.space_before = Pt(1)
        pb_d.text = f"  {b_desc}"
        pb_d.font.name = FONT_BODY
        pb_d.font.size = Pt(11)
        pb_d.font.color.rgb = COLOR_TEXT_WHITE

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s7,
        6.9,
        1.95,
        5.6,
        4.8,
        "Department Bulk Attendance Roster\n(/attendance/department)",
        "Shows department selector, active roster, radio buttons, and conflict warning alert",
    )

    set_speaker_notes(
        s7,
        "Department Bulk Attendance is one of our most critical operational capabilities, designed to streamline daily HR workflows. "
        "The operator selects a department and date, and AttendIQ dynamically generates a roster of all active employees eligible as of that date. "
        "All staff members default to 'Present' for speed, while radio toggles allow immediate adjustments for absences or approved leaves. "
        "To guarantee data integrity, the entire operation executes as an atomic transaction—if a duplicate key is detected, the database automatically rolls back."
    )

    # =========================================================================
    # SLIDE 8: Core Feature: Analytics, Visual Reporting & Employee Profile
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, COLOR_BG_DARK)
    add_header(
        s8,
        "Core Feature Spotlight",
        "Analytics, Headless Visualizations & Drill-Down Profiles",
        "Vectorized cohort aggregations, Matplotlib chart generation, and employee analytics",
    )

    # Left: Details Card
    add_card(s8, 0.8, 1.95, 5.8, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    abox = s8.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.2), Inches(4.4))
    tf_a = abox.text_frame
    tf_a.word_wrap = True
    tf_a.margin_left = tf_a.margin_right = tf_a.margin_top = tf_a.margin_bottom = 0

    p_a1 = tf_a.paragraphs[0]
    p_a1.text = "INTELLIGENCE & VISUAL ANALYTICS SUITE"
    p_a1.font.name = FONT_HEADING
    p_a1.font.size = Pt(15)
    p_a1.font.bold = True
    p_a1.font.color.rgb = COLOR_EMERALD

    a_bullets = [
        ("Executive KPI Dashboard", "Real-time metrics on /: Active Headcount, Overall Attendance %, Absenteeism Rate, Total Eligible Days, and Quick Actions."),
        ("Department & Employee Summaries", "Dynamic cohort aggregation tables (/summary/employees, /summary/departments) with date-range filters and day totals."),
        ("Absenteeism Ranking Leaderboard", "Ranks staff by absenteeism rate on /ranking with color-coded risk tiers (Green ≤5%, Amber ≤15%, Red >15%)."),
        ("Individual Analytics Profile", "Drill-down profile on /employees/<id>/analytics: monthly trend curves, status doughnut chart, and department benchmarks."),
        ("Headless Matplotlib Generation", "Generates high-resolution PNG charts (absenteeism_YYYY-MM.png, monthly_attendance.png) headlessly using the Agg backend."),
    ]

    for b_title, b_desc in a_bullets:
        pb_t = tf_a.add_paragraph()
        pb_t.space_before = Pt(8)
        pb_t.text = f"• {b_title}:"
        pb_t.font.name = FONT_HEADING
        pb_t.font.size = Pt(13)
        pb_t.font.bold = True
        pb_t.font.color.rgb = COLOR_PRIMARY_LIGHT

        pb_d = tf_a.add_paragraph()
        pb_d.space_before = Pt(1)
        pb_d.text = f"  {b_desc}"
        pb_d.font.name = FONT_BODY
        pb_d.font.size = Pt(11)
        pb_d.font.color.rgb = COLOR_TEXT_WHITE

    # Right: Real Generated Matplotlib Chart or Screenshot Placeholder
    # Check if real chart exists
    chart_path = CHARTS_DIR / "absenteeism_2026-09.png"
    if chart_path.exists():
        # Add card container and embed real image
        add_card(s8, 6.9, 1.95, 5.6, 2.7, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
        s8.shapes.add_picture(str(chart_path), Inches(7.0), Inches(2.05), width=Inches(5.4))

        # Bottom box: Placeholder for the web profile screenshot
        add_screenshot_placeholder(
            s8,
            6.9,
            4.8,
            5.6,
            1.95,
            "Employee Analytics Profile (/employees/1/analytics)",
            "Shows KPI cards, monthly trend lines, and department comparison",
        )
    else:
        add_screenshot_placeholder(
            s8,
            6.9,
            1.95,
            5.6,
            4.8,
            "Executive Dashboard & Employee Profile\n(/ and /employees/<id>/analytics)",
            "Shows KPI metric cards, monthly trend chart, and employee distribution",
        )

    set_speaker_notes(
        s8,
        "AttendIQ delivers high-value business intelligence through our analytics module in analysis.py and visualizations.py. "
        "The system calculates cohort performance across departments and flags attendance exceptions without manual spreadsheet manipulation. "
        "On the right, we display an actual Matplotlib chart generated directly by our test pipeline for September 2026, categorizing employee absenteeism into color-coded risk tiers. "
        "Additionally, individual employee profile pages offer deep drill-down analytics, contrasting personal attendance against departmental averages."
    )

    # =========================================================================
    # SLIDE 9: Security Architecture, Governance & Verification
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, COLOR_BG_DARK)
    add_header(
        s9,
        "Governance & Reliability",
        "Security Architecture, Governance & 186 Automated Tests",
        "Defense-in-depth protections and comprehensive test isolation verified with 100% pass rate",
    )

    sec_cards = [
        (
            "Authentication & RBAC",
            "Role separation between Admin (user creation, account toggles) and HR (daily logging). Protects against deactivating the sole remaining Admin.",
            COLOR_PRIMARY_LIGHT,
        ),
        (
            "Dual-Cap Rate Limiter",
            "In-memory sliding window limiter (src/rate_limiter.py) capping 5 failed attempts per user+IP and 20 per IP to thwart brute-force password guessing.",
            COLOR_ROSE,
        ),
        (
            "Immutable Audit Trail",
            "Dedicated attendance_audit table records every CREATE and CORRECT action with operator identity, timestamp, and mandatory correction reasons.",
            COLOR_AMBER,
        ),
        (
            "Defensive Web Hardening",
            "Anti-CSRF synchronizer tokens, 100% parameterized SQL queries (%s), Jinja2 auto-escaping (zero |safe filters), and nosniff / CSP / HSTS headers.",
            COLOR_EMERALD,
        ),
    ]

    card_w = 3.65
    card_h = 2.1
    positions = [
        (0.8, 1.95), (4.8, 1.95), (8.8, 1.95),
        (0.8, 4.3),
    ]

    for (title, text, col), (cx, cy) in zip(sec_cards, positions):
        add_card(s9, cx, cy, card_w, card_h, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
        tbox = s9.shapes.add_textbox(Inches(cx + 0.25), Inches(cy + 0.2), Inches(card_w - 0.5), Inches(card_h - 0.4))
        tf = tbox.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = text
        p2.font.name = FONT_BODY
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_TEXT_WHITE

    # Test Suite Verification Banner (Spanning columns 2 and 3 on the bottom row)
    add_card(s9, 4.8, 4.3, 7.7, 2.1, COLOR_SURFACE_DARK, COLOR_PRIMARY, border_width=1.5)
    vbox = s9.shapes.add_textbox(Inches(5.05), Inches(4.45), Inches(7.2), Inches(1.8))
    tf_v = vbox.text_frame
    tf_v.word_wrap = True
    tf_v.margin_left = tf_v.margin_right = tf_v.margin_top = tf_v.margin_bottom = 0

    pv1 = tf_v.paragraphs[0]
    pv1.text = "VERIFIED TEST EXECUTION SUITE: 186 / 186 PASSED (100%)"
    pv1.font.name = FONT_HEADING
    pv1.font.size = Pt(15)
    pv1.font.bold = True
    pv1.font.color.rgb = COLOR_EMERALD

    pv2 = tf_v.add_paragraph()
    pv2.space_before = Pt(4)
    pv2.text = (
        "• Test Database Isolation: Enforces require_test_database()—tests strictly refuse to touch attendance_db.\n"
        "• Comprehensive Coverage: Unit calculations, SQL injection safety, atomic rollback, CSRF enforcement, "
        "XSS auto-escaping, migration recovery, rate limiter, and reporting period regression."
    )
    pv2.font.name = FONT_BODY
    pv2.font.size = Pt(12)
    pv2.font.color.rgb = COLOR_TEXT_WHITE

    pv3 = tf_v.add_paragraph()
    pv3.space_before = Pt(4)
    pv3.text = "Execution Evidence: 186 passed in 49.07s across 12 pytest modules with zero failures and zero warnings."
    pv3.font.name = FONT_HEADING
    pv3.font.size = Pt(12)
    pv3.font.bold = True
    pv3.font.color.rgb = COLOR_PRIMARY_LIGHT

    set_speaker_notes(
        s9,
        "Enterprise systems require rigorous governance and testing. AttendIQ incorporates a defense-in-depth model featuring "
        "role-based access control, an in-memory dual-cap brute-force rate limiter, and an immutable audit trail table tracking all corrections. "
        "Crucially, our engineering quality is proven by our automated test suite: 186 automated tests execute in under 50 seconds with a 100% pass rate. "
        "Safety guardrails strictly prevent tests from ever modifying the production database, verifying our mathematical and transactional guarantees under all edge conditions."
    )

    # =========================================================================
    # SLIDE 10: Engineering Challenges, Limitations & Conclusion
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, COLOR_BG_DARK)
    add_header(
        s10,
        "Conclusion & Evaluation",
        "Engineering Challenges, Limitations & Academic Conclusion",
        "Key software engineering takeaways, future roadmap, and Q&A discussion",
    )

    # Left: Challenges & Fixes
    add_card(s10, 0.8, 1.95, 5.8, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    c_box = s10.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.2), Inches(4.4))
    tf_c = c_box.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0

    pc1 = tf_c.paragraphs[0]
    pc1.text = "ENGINEERING CHALLENGES OVERCOME"
    pc1.font.name = FONT_HEADING
    pc1.font.size = Pt(15)
    pc1.font.bold = True
    pc1.font.color.rgb = COLOR_PRIMARY_LIGHT

    challenges = [
        ("MySQL Repeatable Read Isolation", "During automated web test fixtures, MySQL's default REPEATABLE READ snapshot masked fresh inserts in test verification connections; resolved by enforcing autocommit on verification connections."),
        ("Zero-Downtime Schema Migration", "Adding joining_date to pre-existing databases risked 1054 Unknown Column errors; built an idempotent migration function in db.py that backfills from earliest attendance rows with zero data loss."),
        ("Strict Architectural Invariants", "Prevented developer slippage by adding automated pytest tests that scan code to ensure zero SQL keywords exist in routes and zero |safe filters exist in templates."),
    ]

    for title, desc in challenges:
        p_t = tf_c.add_paragraph()
        p_t.space_before = Pt(8)
        p_t.text = f"• {title}:"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_AMBER

        p_d = tf_c.add_paragraph()
        p_d.space_before = Pt(1)
        p_d.text = f"  {desc}"
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = COLOR_TEXT_WHITE

    # Right: Limitations, Future Work & Q&A
    add_card(s10, 6.9, 1.95, 5.6, 4.8, COLOR_SURFACE_DARK, COLOR_CARD_BORDER)
    qbox = s10.shapes.add_textbox(Inches(7.2), Inches(2.1), Inches(5.0), Inches(4.4))
    tf_q = qbox.text_frame
    tf_q.word_wrap = True
    tf_q.margin_left = tf_q.margin_right = tf_q.margin_top = tf_q.margin_bottom = 0

    pq1 = tf_q.paragraphs[0]
    pq1.text = "LIMITATIONS & FUTURE ROADMAP"
    pq1.font.name = FONT_HEADING
    pq1.font.size = Pt(15)
    pq1.font.bold = True
    pq1.font.color.rgb = COLOR_ROSE

    pq2 = tf_q.add_paragraph()
    pq2.space_before = Pt(4)
    pq2.text = (
        "• Current Limitations: Attendance is manually entered via Web/CLI; biometric/RFID hardware IoT integration is not yet connected.\n"
        "• Planned Roadmap: Export to Excel/CSV (.xlsx), Azure Power BI App-Owns-Data DirectQuery embed, and mobile push notifications."
    )
    pq2.font.name = FONT_BODY
    pq2.font.size = Pt(11)
    pq2.font.color.rgb = COLOR_TEXT_WHITE

    # Thank you & Questions card inside right column
    pq3 = tf_q.add_paragraph()
    pq3.space_before = Pt(18)
    pq3.text = "THANK YOU!"
    pq3.font.name = FONT_HEADING
    pq3.font.size = Pt(22)
    pq3.font.bold = True
    pq3.font.color.rgb = COLOR_EMERALD

    pq4 = tf_q.add_paragraph()
    pq4.space_before = Pt(4)
    pq4.text = (
        "Batch 4: Ramcharan Reddy, Nikhil, Adarsh, Surekha, Madhavi\n"
        "We welcome questions, suggestions, and feedback from the faculty!"
    )
    pq4.font.name = FONT_HEADING
    pq4.font.size = Pt(13)
    pq4.font.bold = True
    pq4.font.color.rgb = COLOR_PRIMARY_LIGHT

    set_speaker_notes(
        s10,
        "To conclude, developing AttendIQ provided our team with deep practical experience in transactional engineering and enterprise software architecture. "
        "We solved real-world concurrency challenges in MySQL, implemented fault-tolerant schema migrations, and established automated architectural guardrails. "
        "While future releases will incorporate hardware biometric webhooks and Excel exports, AttendIQ stands as a verified, production-ready attendance intelligence platform. "
        "On behalf of Team Batch Four—Ramcharan, Nikhil, Adarsh, Surekha, and Madhavi—we thank our faculty for their guidance, and we welcome your questions."
    )

    # Save presentation
    prs.save(OUTPUT_FILE)
    print(f"Presentation successfully saved to {OUTPUT_FILE.resolve()}")
    return prs


if __name__ == "__main__":
    build_presentation()
