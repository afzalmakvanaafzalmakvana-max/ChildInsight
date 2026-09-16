import io
import csv
from datetime import datetime, timezone, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import reportlab.rl_config
reportlab.rl_config.pageCompression = 0
from app import db
from app.models.child import Child
from app.models.session import ActivitySession
from app.services import analytics_service, recommendation_service, profile_service

DISCLAIMER_TEXT = (
    "Responsible-Use Notice: ChildInsight observes educational interaction patterns to offer learning insights. "
    "It does not evaluate, assess, or diagnose any medical or psychological condition. If persistent learning "
    "challenges are observed, discuss them gently with a qualified educator or counsellor."
)


def _filter_sessions_by_range(child_id, date_range='all'):
    """Returns child's activity sessions filtered by the requested date range."""
    query = ActivitySession.query.filter_by(child_id=child_id)
    now = datetime.now(timezone.utc)

    if date_range == 'weekly':
        since = now - timedelta(days=7)
        query = query.filter(ActivitySession.start_time >= since)
    elif date_range == 'monthly':
        since = now - timedelta(days=30)
        query = query.filter(ActivitySession.start_time >= since)

    return query.order_by(ActivitySession.start_time.desc()).all()


def generate_child_pdf_report(child_id, date_range='all'):
    """Generates a professional PDF educational progress report for a child with the responsible-use disclaimer."""
    child = db.session.get(Child, child_id)
    if not child:
        raise ValueError(f"Child with ID {child_id} not found.")

    snapshot = analytics_service.get_child_analytics_snapshot(child_id)
    recommendations = recommendation_service.get_recommendations_for_child(child_id, persist=False)
    profile_data = profile_service.get_child_learning_pattern_observation(child_id)
    sessions = _filter_sessions_by_range(child_id, date_range)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1F2937')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#6B7280')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2F6FED'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#374151')
    )
    callout_style = ParagraphStyle(
        'DocCallout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#1E40AF')
    )
    disclaimer_style = ParagraphStyle(
        'DocDisclaimer',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#6B7280')
    )

    story = []

    # 1. Header & Metadata
    range_label = 'All Recorded History' if date_range == 'all' else ('Past 7 Days' if date_range == 'weekly' else 'Past 30 Days')
    story.append(Paragraph("ChildInsight — Learning Progress Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y')} &bull; Reporting Window: {range_label}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2F6FED'), spaceBefore=2, spaceAfter=10))

    # Child Information Card Table
    child_info_data = [
        [
            Paragraph(f"<b>Student:</b> {child.name}", body_style),
            Paragraph(f"<b>Age:</b> {child.age or 'Not set'}", body_style),
            Paragraph(f"<b>Grade:</b> {child.grade or 'Not specified'}", body_style),
            Paragraph(f"<b>Language:</b> {child.preferred_language}", body_style)
        ]
    ]
    info_table = Table(child_info_data, colWidths=[130, 90, 150, 160])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # 2. Overall Summary Metrics
    story.append(Paragraph("Overall Performance & Engagement Summary", section_heading))
    metrics_data = [
        ['Metric', 'Score / Value', 'Benchmark Notes'],
        ['Overall Accuracy', f"{snapshot.get('overall_accuracy', 0.0):.1f}%", 'Weighted by total question attempts'],
        ['Completion Rate', f"{snapshot.get('completion_rate', 0.0):.1f}%", f"{snapshot.get('completed_sessions', 0)} of {snapshot.get('total_sessions', 0)} sessions completed"],
        ['Consistency Index', f"{snapshot.get('consistency', 0.0):.1f} / 100", 'Stability across activity sessions'],
        ['Engagement Score', f"{snapshot.get('engagement_index', 0.0):.1f} / 100", 'Multi-signal persistence & curiosity index'],
        ['Composite Performance', f"{snapshot.get('performance_score', 0.0):.1f} / 100", '60% Accuracy + 20% Completion + 20% Consistency']
    ]
    metrics_table = Table(metrics_data, colWidths=[150, 110, 270])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 12))

    # 3. Learning Pattern Engine Observation (Phase 7)
    story.append(Paragraph("Learning Pattern Engine Observation", section_heading))
    raw_obs = profile_data.get('observation', 'No learning pattern observation recorded yet.')
    from app.agent import compliance_agent
    obs_text = compliance_agent.enforce_compliance(
        raw_obs,
        context={'source': 'report', 'child_id': child_id},
        fallback_text="Balanced engagement observed across cognitive learning activities."
    )
    pattern_group = profile_data.get('pattern_group', 'Exploration Pattern')
    obs_data = [
        [
            Paragraph(f"<b>Pattern Group:</b> {pattern_group}<br/><b>Observation:</b> {obs_text}", callout_style)
        ]
    ]
    obs_table = Table(obs_data, colWidths=[530])
    obs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#93C5FD')),
    ]))
    story.append(obs_table)
    story.append(Spacer(1, 12))

    # 4. Domain / Category Breakdown
    story.append(Paragraph("Educational Domain Performance", section_heading))
    cat_breakdown = snapshot.get('category_breakdown', {})
    cat_rows = [['Domain', 'Accuracy', 'Sessions Recorded', 'Status / Focus']]
    for slug, cinfo in cat_breakdown.items():
        acc = cinfo.get('accuracy', 0.0)
        cnt = cinfo.get('sessions_count', 0)
        status_note = 'Strong Performance' if acc >= 80 else ('Steady Progress' if acc >= 50 else 'Practice Opportunity')
        if cnt == 0:
            status_note = 'Not Explored Yet'
        cat_rows.append([cinfo.get('name', slug.capitalize()), f"{acc:.1f}%", str(cnt), status_note])

    cat_table = Table(cat_rows, colWidths=[150, 90, 120, 170])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 12))

    # 5. Tailored Activity Recommendations (Phase 6)
    story.append(Paragraph("Tailored Learning Recommendations (with Explainable Reasons)", section_heading))
    rec_rows = [['Priority', 'Activity', 'Category / Level', 'Reason for Recommendation']]
    for rec in recommendations[:4]:
        rec_rows.append([
            f"#{rec.get('priority', 1)}",
            rec.get('activity_title', 'Activity'),
            f"{rec.get('category_name', '')} ({rec.get('difficulty', '')})",
            Paragraph(rec.get('reason', ''), body_style)
        ])

    if len(rec_rows) > 1:
        rec_table = Table(rec_rows, colWidths=[45, 140, 115, 230])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(rec_table)
    else:
        story.append(Paragraph("No specific recommendations generated yet. Encourage initial activity exploration.", body_style))

    story.append(Spacer(1, 16))

    # 6. Mandatory Responsible-Use Disclaimer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceBefore=8, spaceAfter=8))
    story.append(Paragraph(f"<b>Notice:</b> {DISCLAIMER_TEXT}", disclaimer_style))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def generate_child_csv_report(child_id, date_range='all'):
    """Generates structured CSV educational progress data for a child, including sessions and the responsible-use notice."""
    child = db.session.get(Child, child_id)
    if not child:
        raise ValueError(f"Child with ID {child_id} not found.")

    snapshot = analytics_service.get_child_analytics_snapshot(child_id)
    recommendations = recommendation_service.get_recommendations_for_child(child_id, persist=False)
    profile_data = profile_service.get_child_learning_pattern_observation(child_id)
    sessions = _filter_sessions_by_range(child_id, date_range)

    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Child Profile Metadata
    writer.writerow(['CHILDINSIGHT EDUCATIONAL PROGRESS REPORT'])
    writer.writerow(['Generated At', datetime.now(timezone.utc).isoformat()])
    writer.writerow(['Reporting Range', date_range])
    writer.writerow([])
    writer.writerow(['STUDENT PROFILE'])
    writer.writerow(['Child ID', child.id])
    writer.writerow(['Name', child.name])
    writer.writerow(['Age', child.age or 'N/A'])
    writer.writerow(['Grade', child.grade or 'N/A'])
    writer.writerow(['Preferred Language', child.preferred_language])
    writer.writerow([])

    # Section 2: Summary Analytics
    writer.writerow(['OVERALL ANALYTICS SUMMARY'])
    writer.writerow(['Metric', 'Value', 'Description'])
    writer.writerow(['Overall Accuracy', f"{snapshot.get('overall_accuracy', 0.0):.2f}%", 'Weighted accuracy by question attempts'])
    writer.writerow(['Completion Rate', f"{snapshot.get('completion_rate', 0.0):.2f}%", 'Percentage of initiated sessions completed'])
    writer.writerow(['Consistency Score', f"{snapshot.get('consistency', 0.0):.2f}", 'Score out of 100 based on standard deviation'])
    writer.writerow(['Engagement Index', f"{snapshot.get('engagement_index', 0.0):.2f}", 'Multi-signal engagement score'])
    writer.writerow(['Composite Performance Score', f"{snapshot.get('performance_score', 0.0):.2f}", 'Weighted formula (60% Acc + 20% Comp + 20% Cons)'])
    writer.writerow([])

    # Section 3: Learning Pattern Observation
    writer.writerow(['LEARNING PATTERN ENGINE (ML)'])
    raw_obs = profile_data.get('observation', 'None')
    from app.agent import compliance_agent
    clean_obs = compliance_agent.enforce_compliance(
        raw_obs,
        context={'source': 'report', 'child_id': child_id},
        fallback_text="Balanced engagement observed across cognitive learning activities."
    )
    writer.writerow(['Pattern Group', profile_data.get('pattern_group', 'Exploration')])
    writer.writerow(['Observation', clean_obs])
    writer.writerow([])

    # Section 4: Domain Performance Breakdown
    writer.writerow(['CATEGORY BREAKDOWN'])
    writer.writerow(['Category Name', 'Slug', 'Accuracy (%)', 'Sessions Count'])
    for slug, cinfo in snapshot.get('category_breakdown', {}).items():
        writer.writerow([cinfo.get('name', slug), slug, f"{cinfo.get('accuracy', 0.0):.2f}", cinfo.get('sessions_count', 0)])
    writer.writerow([])

    # Section 5: Activity Sessions Log
    writer.writerow(['SESSION LOG'])
    writer.writerow(['Session ID', 'Activity Title', 'Category', 'Difficulty', 'Attempts', 'Correct', 'Accuracy (%)', 'Duration (s)', 'Status', 'Date'])
    for s in sessions:
        act = s.activity
        cat_name = act.category.name if act and act.category else 'N/A'
        act_title = act.title if act else 'N/A'
        act_diff = act.difficulty if act else 'N/A'
        start_str = s.start_time.isoformat() if s.start_time else ''
        writer.writerow([s.id, act_title, cat_name, act_diff, s.attempts, s.correct_answers, f"{s.accuracy:.2f}", s.duration_seconds, s.status, start_str])
    writer.writerow([])

    # Section 6: Tailored Recommendations
    writer.writerow(['RECOMMENDATIONS'])
    writer.writerow(['Priority', 'Activity Title', 'Category', 'Difficulty', 'Recommendation Type', 'Reason'])
    for rec in recommendations:
        clean_reason = compliance_agent.enforce_compliance(
            rec.get('reason', ''),
            context={'source': 'report', 'child_id': child_id},
            fallback_text="Practice suggested to reinforce core skills."
        )
        writer.writerow([rec.get('priority'), rec.get('activity_title'), rec.get('category_name'), rec.get('difficulty'), rec.get('recommendation_type'), clean_reason])
    writer.writerow([])

    # Section 7: Mandatory Responsible-Use Notice
    writer.writerow(['RESPONSIBLE-USE NOTICE'])
    writer.writerow([DISCLAIMER_TEXT])

    return output.getvalue()
