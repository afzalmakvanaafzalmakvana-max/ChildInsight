"""
AI-Assisted Content Drafting Agent (app/agent/content_draft_agent.py)

Generates research-grounded, age-appropriate educational activity drafts for
administrator review. The agent uses real platform context:
1. Target category's existing activities (style/tone reference)
2. Specific age-band content across all categories (difficulty calibration)
3. Content Suggestion reason text (addressing specific detected gaps)
4. Compliance Agent blacklist rules (embedded negative generation constraints)

CRITICAL RULE: This agent NEVER auto-publishes or writes directly to activities
tables. All drafts are returned in-memory for explicit human review and editing.
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
import urllib.request
import urllib.error

from app import db
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import compliance_agent

logger = logging.getLogger('childinsight.content_draft_agent')

AGE_BANDS = {
    '4-6': {'min_age': 4, 'max_age': 6, 'label': 'Ages 4-6 (Early Childhood / Pre-K)', 'default_duration': 5},
    '6-9': {'min_age': 6, 'max_age': 9, 'label': 'Ages 6-9 (Early Elementary)', 'default_duration': 8},
    '9-12': {'min_age': 9, 'max_age': 12, 'label': 'Ages 9-12 (Upper Elementary)', 'default_duration': 10},
    '12-14': {'min_age': 12, 'max_age': 14, 'label': 'Ages 12-14 (Early Secondary)', 'default_duration': 12}
}


# =============================================================================
# 1. PLATFORM CONTEXT EXTRACTION HELPERS
# =============================================================================

def get_category_style_context(category_id: int) -> dict:
    """Fetches real existing activities in the target category as tone/style references."""
    category = db.session.get(Category, category_id)
    if not category:
        return {'category_name': 'General Learning', 'category_slug': 'general', 'reference_activities': []}

    activities = Activity.query.filter_by(category_id=category_id, is_active=True).limit(6).all()
    sample_activities = []
    for act in activities:
        q_sample = [q.question_text for q in act.questions[:2]]
        sample_activities.append({
            'title': act.title,
            'difficulty': act.difficulty,
            'min_age': act.min_age,
            'max_age': act.max_age,
            'description': act.description,
            'sample_questions': q_sample
        })

    return {
        'category_name': category.name,
        'category_slug': category.slug,
        'category_description': category.description,
        'reference_activities': sample_activities
    }


def get_age_band_calibration_context(min_age: int, max_age: int, exclude_category_id: int = None) -> list:
    """
    Fetches existing activities across ALL categories for the target age band
    to ground difficulty calibration, vocabulary level, and cognitive expectations.
    """
    query = Activity.query.filter(
        Activity.is_active == True,
        Activity.min_age <= max_age,
        Activity.max_age >= min_age
    )
    if exclude_category_id:
        query = query.filter(Activity.category_id != exclude_category_id)

    activities = query.order_by(Activity.id.asc()).limit(8).all()
    calibration = []
    for act in activities:
        calibration.append({
            'title': act.title,
            'category_name': act.category.name if act.category else 'General',
            'difficulty': act.difficulty,
            'age_band': f"{act.min_age}-{act.max_age}",
            'description': act.description
        })
    return calibration


def get_suggestion_context(suggestion_id: int | None) -> dict | None:
    """Extracts gap detection reasoning and metadata from a linked ContentSuggestion."""
    if not suggestion_id:
        return None
    suggestion = db.session.get(ContentSuggestion, suggestion_id)
    if not suggestion:
        return None

    return {
        'id': suggestion.id,
        'suggestion_type': suggestion.suggestion_type,
        'suggested_title': suggestion.suggested_title,
        'target_difficulty': suggestion.target_difficulty,
        'age_band': suggestion.age_band,
        'reason': suggestion.reason
    }


# =============================================================================
# 2. PROMPT COMPILATION WITH REAL CONTEXT & COMPLIANCE CONSTRAINTS
# =============================================================================

def build_generation_prompt(
    category_id: int,
    age_band_key: str,
    difficulty: str,
    custom_guidance: str = None,
    suggestion_id: int = None
) -> tuple[str, str, dict]:
    """
    Constructs the system prompt and grounded user prompt embedding:
    - Real existing activity titles in category
    - Cross-category age-band calibration activities
    - Content suggestion gap reason text
    - Explicit PRD §4 compliance blacklist constraints

    Returns (system_prompt, user_prompt, platform_context_meta).
    """
    band_info = AGE_BANDS.get(age_band_key, AGE_BANDS['6-9'])
    min_age = band_info['min_age']
    max_age = band_info['max_age']

    cat_context = get_category_style_context(category_id)
    calibration_context = get_age_band_calibration_context(min_age, max_age, exclude_category_id=category_id)
    sugg_context = get_suggestion_context(suggestion_id)
    is_translation_gap = bool(sugg_context and sugg_context.get('suggestion_type') == ContentSuggestion.TYPE_TRANSLATION_GAP)

    matched_tone_titles = [a['title'] for a in cat_context['reference_activities']]
    calibration_titles = [f"{a['title']} ({a['category_name']}, {a['difficulty']})" for a in calibration_context[:5]]

    if is_translation_gap:
        output_format_instructions = (
            "OUTPUT FORMAT (DUAL-LANGUAGE DRAFT REQUIRED):\n"
            "You must respond ONLY with a valid JSON object matching this structure containing BOTH English and Hindi versions:\n"
            "{\n"
            '  "title": "Activity Title (English, playful, engaging)",\n'
            '  "description": "Short 1-2 sentence description in English.",\n'
            '  "estimated_duration": 8,\n'
            '  "questions": [\n'
            '    {\n'
            '      "question_text": "Engaging question text in English",\n'
            '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
            '      "correct_answer": "Option A",\n'
            '      "hint": "Gentle, supportive clue in English."\n'
            '    }\n'
            '  ],\n'
            '  "translations": {\n'
            '    "hi": {\n'
            '      "title": "हिंदी शीर्षक (Playful Hindi Title)",\n'
            '      "description": "हिंदी विवरण (Short 1-2 sentence description in Hindi)",\n'
            '      "questions": [\n'
            '        {\n'
            '          "question_text": "हिंदी प्रश्न (Engaging Hindi question prompt)",\n'
            '          "options": ["विकल्प क", "विकल्प ख", "विकल्प ग", "विकल्प घ"],\n'
            '          "correct_answer": "विकल्प क",\n'
            '          "hint": "सहायक संकेत (Scaffolding clue in Hindi)"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  }\n'
            "}"
        )
    else:
        output_format_instructions = (
            "OUTPUT FORMAT:\n"
            "You must respond ONLY with a valid JSON object matching this structure (no markdown formatting or wrapping outside JSON):\n"
            "{\n"
            '  "title": "Activity Title (playful, engaging)",\n'
            '  "description": "Short 1-2 sentence description setting up the playful scenario.",\n'
            '  "estimated_duration": 8,\n'
            '  "questions": [\n'
            '    {\n'
            '      "question_text": "Engaging question text suitable for the age band",\n'
            '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
            '      "correct_answer": "Option A",\n'
            '      "hint": "Gentle, supportive clue that scaffolds understanding."\n'
            '    }\n'
            '  ]\n'
            "}"
        )

    system_prompt = (
        "You are an expert pedagogical content designer for 'ChildInsight', an intelligent "
        "developmental learning system for children aged 4-14.\n\n"
        "CORE PEDAGOGICAL PHILOSOPHY:\n"
        "- All activities must be playful, encouraging, game-like adventure quests (e.g. detective mysteries, "
        "nature safaris, space journeys, magical code puzzles). NEVER make them feel like exams, tests, or worksheets.\n"
        "- Match developmental capabilities for the target age group accurately.\n"
        "- Provide 5 to 6 engaging multiple-choice questions. Each question must have exactly 4 options "
        "and exactly 1 unambiguous correct answer.\n\n"
        "STRICT ETHICAL & COMPLIANCE CONSTRAINTS (PRD §4):\n"
        "- You must NEVER use clinical, psychological, or diagnostic terminology in any title, description, question, or hint in ANY language.\n"
        "- FORBIDDEN ENGLISH TERMS:\n"
        f"  {', '.join(compliance_agent.FORBIDDEN_TERMS)}\n"
        "- FORBIDDEN HINDI TERMS:\n"
        f"  {', '.join(compliance_agent.FORBIDDEN_TERMS_HI)}\n"
        "- Do not evaluate IQ, mental capacity, or deficit. Focus strictly on creative and cheerful problem solving.\n\n"
        f"{output_format_instructions}"
    )

    user_prompt_lines = [
        f"TARGET DOMAIN: {cat_context['category_name']} ({cat_context['category_description']})",
        f"TARGET AGE BAND: {band_info['label']} (Ages {min_age}-{max_age})",
        f"TARGET DIFFICULTY: {difficulty}",
    ]

    if sugg_context:
        user_prompt_lines.append(f"\nIDENTIFIED CURRICULUM GAP TO ADDRESS:")
        user_prompt_lines.append(f"- Suggestion Type: {sugg_context['suggestion_type']}")
        user_prompt_lines.append(f"- Data-Backed Reason: {sugg_context['reason']}")
        if sugg_context.get('suggested_title'):
            user_prompt_lines.append(f"- Suggested Title Idea: {sugg_context['suggested_title']}")

    if custom_guidance:
        user_prompt_lines.append(f"\nADMINISTRATOR FOCUS / TOPIC GUIDANCE:\n{custom_guidance.strip()}")

    if matched_tone_titles:
        user_prompt_lines.append(f"\nEXISTING ACTIVITIES IN THIS CATEGORY (STYLE & TONE REFERENCE):")
        for title in matched_tone_titles[:5]:
            user_prompt_lines.append(f"- {title}")

    if calibration_titles:
        user_prompt_lines.append(f"\nCROSS-CATEGORY CONTENT CALIBRATION FOR AGES {min_age}-{max_age}:")
        for item in calibration_titles:
            user_prompt_lines.append(f"- {item}")

    user_prompt_lines.append(
        f"\nCreate an original {difficulty}-level activity for {cat_context['category_name']} "
        f"for ages {min_age}-{max_age} containing 5-6 questions. Make sure the difficulty aligns "
        f"with the calibration examples and the tone is encouraging and playful."
    )

    user_prompt = "\n".join(user_prompt_lines)

    platform_context_meta = {
        'category_id': category_id,
        'category_name': cat_context['category_name'],
        'age_band': age_band_key,
        'min_age': min_age,
        'max_age': max_age,
        'difficulty': difficulty,
        'matched_tone_titles': matched_tone_titles[:5],
        'calibration_titles': calibration_titles[:5],
        'suggestion_id': sugg_context['id'] if sugg_context else None,
        'addressed_gap_reason': sugg_context['reason'] if sugg_context else None,
        'compliance_constraints_applied': True
    }

    return system_prompt, user_prompt, platform_context_meta


# =============================================================================
# 3. ANTHROPIC API CLIENT & GROUNDED FALLBACK GENERATOR
# =============================================================================

def _call_anthropic_api(system_prompt: str, user_prompt: str) -> dict:
    """
    Invokes the Anthropic API requesting structured JSON using the standard
    Messages API (claude-3-5-sonnet-20241022).
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": model,
        "max_tokens": 2500,
        "temperature": 0.4,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=30) as response:
        res_body = response.read().decode('utf-8')
        res_json = json.loads(res_body)

    # Extract assistant text content
    content_blocks = res_json.get('content', [])
    raw_text = "".join(b.get('text', '') for b in content_blocks if b.get('type') == 'text')

    # Parse JSON (stripping markdown fences if returned)
    cleaned = raw_text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    return json.loads(cleaned.strip())


def _generate_grounded_fallback(
    category_name: str,
    age_band_key: str,
    difficulty: str,
    suggestion_context: dict = None,
    custom_guidance: str = None,
    is_translation_gap: bool = False
) -> dict:
    """
    High-quality, platform-grounded fallback generator used when ANTHROPIC_API_KEY
    is not set or in offline/test environments.
    Strictly follows PRD §4 non-diagnostic tone and age calibration.
    When is_translation_gap is True, provides paired Hindi content.
    """
    band_info = AGE_BANDS.get(age_band_key, AGE_BANDS['6-9'])
    min_age = band_info['min_age']
    max_age = band_info['max_age']

    # Use suggestion suggested_title if provided
    base_title = None
    if suggestion_context and suggestion_context.get('suggested_title'):
        base_title = suggestion_context['suggested_title']
    elif custom_guidance:
        # derive a title from guidance
        clean_g = re.sub(r'[^\w\s]', '', custom_guidance).strip().title()
        words = clean_g.split()[:4]
        base_title = " ".join(words) + " Quest"

    if not base_title:
        title_templates = {
            'Visual Learning': f"Secret Canvas & Optical Clues ({difficulty})",
            'Logic': f"Mystery Island Code Quest ({difficulty})",
            'Numbers': f"Number Safari Expedition ({difficulty})",
            'Language': f"Word Garden Riddle Adventure ({difficulty})",
            'Memory': f"Treasure Chest Memory Recall ({difficulty})"
        }
        base_title = title_templates.get(category_name, f"Curious Explorer Adventure ({difficulty})")

    description = (
        f"Embark on an interactive {category_name.lower()} challenge designed for learners aged {min_age}-{max_age}. "
        "Work through engaging clues, observe carefully, and unlock discovery badges!"
    )

    # Generate 5 curated, developmentally calibrated questions for fallback
    if min_age <= 6:
        questions = [
            {
                "question_text": "Which friendly color appears when blue ocean water and bright yellow sun mix?",
                "options": ["Green", "Red", "Purple", "Black"],
                "correct_answer": "Green",
                "hint": "Think of green grass or tree leaves!"
            },
            {
                "question_text": "Look at the pattern: Star, Circle, Star, Circle, Star... What comes next?",
                "options": ["Circle", "Square", "Triangle", "Star"],
                "correct_answer": "Circle",
                "hint": "Follow the alternating rhythm: Star then Circle."
            },
            {
                "question_text": "How many friendly puppies are playing if there are 2 brown puppies and 2 white puppies?",
                "options": ["4", "3", "5", "6"],
                "correct_answer": "4",
                "hint": "Count them up: 1, 2, 3, 4 puppies!"
            },
            {
                "question_text": "Which animal makes a cheerful 'Ribbit' sound near the pond?",
                "options": ["Frog", "Duck", "Horse", "Bear"],
                "correct_answer": "Frog",
                "hint": "It loves jumping on lily pads."
            },
            {
                "question_text": "Which of these shapes has no pointy corners at all and rolls smoothly?",
                "options": ["Circle", "Triangle", "Square", "Rectangle"],
                "correct_answer": "Circle",
                "hint": "Think of a round coin or a basketball."
            }
        ]
        hi_questions = [
            {
                "question_text": "जब नीले समुद्र का पानी और चमकीला पीला सूरज मिलते हैं, तो कौन सा सुंदर रंग बनता है?",
                "options": ["हरा", "लाल", "बैंगनी", "काला"],
                "correct_answer": "हरा",
                "hint": "हरी घास या पेड़ों की पत्तियों के बारे में सोचें!"
            },
            {
                "question_text": "इस पैटर्न को देखें: तारा, वृत्त, तारा, वृत्त, तारा... आगे क्या आएगा?",
                "options": ["वृत्त", "वर्ग", "त्रिकोण", "तारा"],
                "correct_answer": "वृत्त",
                "hint": "बारी-बारी से आने वाले क्रम को देखें: तारा फिर वृत्त।"
            },
            {
                "question_text": "यदि 2 भूरे पिल्ले और 2 सफेद पिल्ले खेल रहे हैं, तो कुल कितने पिल्ले खेल रहे हैं?",
                "options": ["4", "3", "5", "6"],
                "correct_answer": "4",
                "hint": "उन्हें गिनें: 1, 2, 3, 4 पिल्ले!"
            },
            {
                "question_text": "तालाब के पास कौन सा प्यारा जानवर टर्र-टर्र की आवाज निकालता है?",
                "options": ["मेंढक", "बत्तख", "घोड़ा", "भालू"],
                "correct_answer": "मेंढक",
                "hint": "यह कमल के पत्तों पर कूदना पसंद करता है।"
            },
            {
                "question_text": "इनमें से किस आकार का कोई नुकीला कोना नहीं होता और वह आसानी से लुढ़कता है?",
                "options": ["वृत्त", "त्रिकोण", "वर्ग", "आयत"],
                "correct_answer": "वृत्त",
                "hint": "एक गोल सिक्के या गेंद के बारे में सोचें।"
            }
        ]
    elif min_age <= 9:
        questions = [
            {
                "question_text": "Find the missing number in this ascending step sequence: 4, 8, 12, __, 20.",
                "options": ["16", "14", "15", "18"],
                "correct_answer": "16",
                "hint": "Notice that each step adds 4 to the previous number."
            },
            {
                "question_text": "Which word is an enthusiastic synonym for 'joyful'?",
                "options": ["Delighted", "Tired", "Gloomy", "Quiet"],
                "correct_answer": "Delighted",
                "hint": "Think of celebrating good news with a broad smile."
            },
            {
                "question_text": "If a square garden has sides that are each 5 meters long, what is the total distance around it?",
                "options": ["20 meters", "25 meters", "15 meters", "10 meters"],
                "correct_answer": "20 meters",
                "hint": "Add all 4 equal sides: 5 + 5 + 5 + 5."
            },
            {
                "question_text": "Which object belongs in this group: Compass, Map, Binoculars, Telescope, and...?",
                "options": ["Flashlight", "Pillow", "Banana", "Spoon"],
                "correct_answer": "Flashlight",
                "hint": "Select the tool an explorer uses on an expedition."
            },
            {
                "question_text": "Maya has 3 blue marbles, 4 green marbles, and 5 red marbles. How many marbles does she have altogether?",
                "options": ["12", "11", "10", "14"],
                "correct_answer": "12",
                "hint": "Add 3 + 4 = 7, then add 5."
            }
        ]
        hi_questions = [
            {
                "question_text": "इस बढ़ती संख्या श्रृंखला में छूटी हुई संख्या ज्ञात करें: 4, 8, 12, __, 20।",
                "options": ["16", "14", "15", "18"],
                "correct_answer": "16",
                "hint": "ध्यान दें कि प्रत्येक चरण में पिछली संख्या में 4 जोड़ा जाता है।"
            },
            {
                "question_text": "'प्रसन्न' (आनंदित) शब्द का सबसे उपयुक्त पर्यायवाची शब्द कौन सा है?",
                "options": ["उल्लसित", "थका हुआ", "उदास", "शांत"],
                "correct_answer": "उल्लसित",
                "hint": "मुस्कान के साथ अच्छी खबर मनाने के बारे में सोचें।"
            },
            {
                "question_text": "यदि एक वर्गाकार बगीचे की प्रत्येक भुजा 5 मीटर लंबी है, तो उसका कुल घेरा (परिमाप) कितना होगा?",
                "options": ["20 मीटर", "25 मीटर", "15 मीटर", "10 मीटर"],
                "correct_answer": "20 मीटर",
                "hint": "सभी 4 बराबर भुजाओं को जोड़ें: 5 + 5 + 5 + 5।"
            },
            {
                "question_text": "इस समूह में कौन सी वस्तु उपयुक्त है: दिशा-सूचक यंत्र, नक्शा, दूरबीन और...?",
                "options": ["टॉर्च", "तकिया", "केला", "चम्मच"],
                "correct_answer": "टॉर्च",
                "hint": "उस उपकरण को चुनें जिसका उपयोग एक खोजकर्ता यात्रा पर करता है।"
            },
            {
                "question_text": "माया के पास 3 नीले कंचे, 4 हरे कंचे और 5 लाल कंचे हैं। उसके पास कुल कितने कंचे हैं?",
                "options": ["12", "11", "10", "14"],
                "correct_answer": "12",
                "hint": "3 + 4 = 7 जोड़ें, फिर उसमें 5 और जोड़ें।"
            }
        ]
    elif min_age <= 12:
        questions = [
            {
                "question_text": "If all Zips are Zaps, and some Zaps are Zooms, which conclusion is definitely true?",
                "options": [
                    "All Zips are Zaps",
                    "All Zooms are Zips",
                    "No Zips can be Zooms",
                    "All Zaps are Zips"
                ],
                "correct_answer": "All Zips are Zaps",
                "hint": "Look directly at the first premise given."
            },
            {
                "question_text": "Which fraction represents the largest portion of a whole?",
                "options": ["3/4", "2/3", "1/2", "5/8"],
                "correct_answer": "3/4",
                "hint": "Compare their decimal equivalents: 3/4 is 0.75."
            },
            {
                "question_text": "Which word best completes the analogy? Telescope is to Astronomy as Microscope is to...",
                "options": ["Biology", "Geology", "Aeronautics", "Meteorology"],
                "correct_answer": "Biology",
                "hint": "Microscopes let scientists examine cells and tiny organisms."
            },
            {
                "question_text": "A code replaces each letter with its position in the alphabet (A=1, B=2). What word is spelled by: 3-1-20?",
                "options": ["CAT", "BAT", "DOG", "CAR"],
                "correct_answer": "CAT",
                "hint": "3rd letter is C, 1st letter is A, 20th letter is T."
            },
            {
                "question_text": "A train travels at a constant speed of 60 km/h. How far does it travel in 2 hours and 30 minutes?",
                "options": ["150 km", "120 km", "180 km", "140 km"],
                "correct_answer": "150 km",
                "hint": "Multiply 60 by 2.5 hours."
            }
        ]
        hi_questions = [
            {
                "question_text": "यदि सभी 'क' वस्तुएं 'ख' हैं, और कुछ 'ख' वस्तुएं 'ग' हैं, तो कौन सा निष्कर्ष निश्चित रूप से सत्य है?",
                "options": [
                    "सभी 'क' वस्तुएं 'ख' हैं",
                    "सभी 'ग' वस्तुएं 'क' हैं",
                    "कोई 'क' वस्तु 'ग' नहीं हो सकती",
                    "सभी 'ख' वस्तुएं 'क' हैं"
                ],
                "correct_answer": "सभी 'क' वस्तुएं 'ख' हैं",
                "hint": "दिए गए पहले नियम को सीधे देखें।"
            },
            {
                "question_text": "इनमें से कौन सा भिन्न सबसे बड़े हिस्से को दर्शाता है?",
                "options": ["3/4", "2/3", "1/2", "5/8"],
                "correct_answer": "3/4",
                "hint": "दशमलव मान की तुलना करें: 3/4 का मान 0.75 होता है।"
            },
            {
                "question_text": "समानता को कौन सा शब्द पूरा करता है? दूरबीन का खगोल विज्ञान से वही संबंध है जो सूक्ष्मदर्शी का... से है।",
                "options": ["जीव विज्ञान", "भूविज्ञान", "विमानिकी", "मौसम विज्ञान"],
                "correct_answer": "जीव विज्ञान",
                "hint": "सूक्ष्मदर्शी की मदद से वैज्ञानिक कोशिकाओं का अध्ययन करते हैं।"
            },
            {
                "question_text": "एक गुप्त कोड में प्रत्येक अक्षर को वर्णमाला में उसके स्थान से बदला जाता है (A=1, B=2)। 3-1-20 से कौन सा शब्द बनता है?",
                "options": ["CAT", "BAT", "DOG", "CAR"],
                "correct_answer": "CAT",
                "hint": "तीसरा अक्षर C है, पहला अक्षर A है, और 20वाँ अक्षर T है।"
            },
            {
                "question_text": "एक रेलगाड़ी 60 किमी/घंटा की समान गति से चलती है। वह 2 घंटे 30 मिनट में कितनी दूरी तय करेगी?",
                "options": ["150 किमी", "120 किमी", "180 किमी", "140 किमी"],
                "correct_answer": "150 किमी",
                "hint": "60 को 2.5 घंटे से गुणा करें।"
            }
        ]
    else:  # 12-14
        questions = [
            {
                "question_text": "If 3x + 7 = 28, what is the value of x?",
                "options": ["7", "6", "8", "9"],
                "correct_answer": "7",
                "hint": "Subtract 7 from both sides to get 3x = 21, then divide by 3."
            },
            {
                "question_text": "Which literary device is demonstrated in: 'The ancient trees whispered secrets in the twilight breeze'?",
                "options": ["Personification", "Hyperbole", "Alliteration", "Onomatopoeia"],
                "correct_answer": "Personification",
                "hint": "Human actions (whispering secrets) are attributed to trees."
            },
            {
                "question_text": "Four friends sit in a row. Liam is not at either end. Sarah sits immediately to Liam's right. If Liam is in position 2, where is Sarah?",
                "options": ["Position 3", "Position 1", "Position 4", "Position 2"],
                "correct_answer": "Position 3",
                "hint": "Position immediately to the right of position 2 is position 3."
            },
            {
                "question_text": "What is the probability of rolling an odd number greater than 2 on a standard 6-sided die?",
                "options": ["2/6 (or 1/3)", "3/6 (or 1/2)", "1/6", "4/6 (or 2/3)"],
                "correct_answer": "2/6 (or 1/3)",
                "hint": "The odd numbers on a die are 1, 3, 5. Those greater than 2 are 3 and 5 (2 numbers out of 6)."
            },
            {
                "question_text": "Which argument demonstrates deductive rather than inductive reasoning?",
                "options": [
                    "All prime numbers greater than 2 are odd; 17 is a prime greater than 2; therefore, 17 is odd.",
                    "The sun has risen every morning so far, so it will probably rise tomorrow.",
                    "Most students enjoy games, so Oliver will likely enjoy this game.",
                    "Every swan observed on the lake was white, so all swans must be white."
                ],
                "correct_answer": "All prime numbers greater than 2 are odd; 17 is a prime greater than 2; therefore, 17 is odd.",
                "hint": "Deductive reasoning guarantees the conclusion follows necessarily from true general premises."
            }
        ]
        hi_questions = [
            {
                "question_text": "यदि 3x + 7 = 28 है, तो x का मान क्या होगा?",
                "options": ["7", "6", "8", "9"],
                "correct_answer": "7",
                "hint": "दोनों तरफ से 7 घटाएं जिससे 3x = 21 मिले, फिर 3 से भाग दें।"
            },
            {
                "question_text": "इस पंक्ति में कौन सा साहित्यिक अलंकार प्रकट होता है: 'प्राचीन वृक्ष सांझ की हवा में रहस्य फुसफुसा रहे थे'?",
                "options": ["मानवीकरण", "अतिशयोक्ति", "अनुप्रास", "ध्वन्यानुकरण"],
                "correct_answer": "मानवीकरण",
                "hint": "वृक्षों को इंसानों की तरह फुसफुसाने का मानवीय गुण दिया गया है।"
            },
            {
                "question_text": "चार मित्र एक पंक्ति में बैठे हैं। कबीर किसी भी छोर पर नहीं है। सारा, कबीर के ठीक दाईं ओर बैठती है। यदि कबीर दूसरे स्थान पर है, तो सारा कहाँ है?",
                "options": ["तीसरे स्थान पर", "पहले स्थान पर", "चौथे स्थान पर", "दूसरे स्थान पर"],
                "correct_answer": "तीसरे स्थान पर",
                "hint": "स्थान 2 के ठीक दाईं ओर का स्थान 3 होता है।"
            },
            {
                "question_text": "एक मानक 6-फलकीय पासे को फेंकने पर 2 से बड़ी विषम संख्या आने की प्रायिकता क्या है?",
                "options": ["2/6 (या 1/3)", "3/6 (या 1/2)", "1/6", "4/6 (या 2/3)"],
                "correct_answer": "2/6 (या 1/3)",
                "hint": "पासे पर विषम संख्याएँ 1, 3, 5 हैं। 2 से बड़ी केवल 3 और 5 हैं (6 में से 2)।"
            },
            {
                "question_text": "कौन सा तर्क आगमनात्मक के बजाय निगमनात्मक (Deductive) तर्क को दर्शाता है?",
                "options": [
                    "2 से बड़ी सभी अभाज्य संख्याएँ विषम होती हैं; 17, 2 से बड़ी एक अभाज्य संख्या है; इसलिए, 17 विषम है।",
                    "सूरज अब तक हर सुबह निकला है, इसलिए शायद कल भी निकलेगा।",
                    "अधिकांश बच्चे खेल पसंद करते हैं, इसलिए रोहन भी शायद यह खेल पसंद करेगा।",
                    "झील पर देखे गए सभी हंस सफेद थे, इसलिए सभी हंस सफेद होने चाहिए।"
                ],
                "correct_answer": "2 से बड़ी सभी अभाज्य संख्याएँ विषम होती हैं; 17, 2 से बड़ी एक अभाज्य संख्या है; इसलिए, 17 विषम है।",
                "hint": "निगमनात्मक तर्क में सत्य सामान्य आधार से निष्कर्ष अनिवार्य रूप से निकलता है।"
            }
        ]

    result = {
        "title": base_title,
        "description": description,
        "estimated_duration": band_info['default_duration'],
        "questions": questions
    }

    if is_translation_gap:
        category_names_hi = {
            'Visual Learning': 'दृश्य अधिगम',
            'Logic': 'तर्क शक्ति',
            'Numbers': 'संख्या ज्ञान',
            'Language': 'भाषा ज्ञान',
            'Memory': 'स्मृति अभ्यास'
        }
        hi_cat = category_names_hi.get(category_name, 'रोमांचक')
        hi_title = f"{hi_cat} खोज यात्रा ({difficulty})"
        hi_description = (
            f"{min_age}-{max_age} वर्ष के बच्चों के लिए {hi_cat} सीखने की गतिविधि। "
            "पहेलियाँ सुलझाएँ और नए बैज प्राप्त करें!"
        )
        result["translations"] = {
            "hi": {
                "title": hi_title,
                "description": hi_description,
                "questions": hi_questions
            }
        }

    return result


# =============================================================================
# 4. SECOND-LAYER COMPLIANCE VERIFICATION & RETRY LOGIC
# =============================================================================

def verify_and_clean_questions(
    raw_questions: list,
    category_name: str,
    age_band_key: str,
    raw_hi_questions: list = None
) -> tuple[list, list, int]:
    """
    Runs every generated question through compliance_agent.check_text()
    for BOTH English and Hindi content.
    If a question contains clinical/diagnostic terms in either language:
    - Retries generating a clean replacement up to 2 times
    - If it still fails after 2 retries, it is discarded/skipped.
    Returns (cleaned_en_questions, cleaned_hi_questions, discarded_count).
    """
    cleaned_en_questions = []
    cleaned_hi_questions = []
    discarded_count = 0

    has_hi = bool(raw_hi_questions and len(raw_hi_questions) > 0)

    for idx, q in enumerate(raw_questions):
        q_text = q.get('question_text', '')
        options = q.get('options', [])
        correct_answer = q.get('correct_answer', '')
        hint = q.get('hint', '')

        # Check English text elements
        is_safe, reason = compliance_agent.check_text(q_text)
        if is_safe:
            is_safe, reason = compliance_agent.check_text(correct_answer)
        if is_safe:
            is_safe, reason = compliance_agent.check_text(hint)
        if is_safe:
            for opt in options:
                is_safe, reason = compliance_agent.check_text(opt)
                if not is_safe:
                    break

        # Check Hindi text elements if present
        hi_q = raw_hi_questions[idx] if has_hi and idx < len(raw_hi_questions) else None
        if is_safe and hi_q:
            hi_q_text = hi_q.get('question_text', '')
            hi_options = hi_q.get('options', [])
            hi_correct = hi_q.get('correct_answer', '')
            hi_hint = hi_q.get('hint', '')

            is_safe, reason = compliance_agent.check_text(hi_q_text)
            if is_safe:
                is_safe, reason = compliance_agent.check_text(hi_correct)
            if is_safe:
                is_safe, reason = compliance_agent.check_text(hi_hint)
            if is_safe:
                for hopt in hi_options:
                    is_safe, reason = compliance_agent.check_text(hopt)
                    if not is_safe:
                        break

        if is_safe:
            # Format cleanly
            if correct_answer not in options and options:
                options[0] = correct_answer

            order = len(cleaned_en_questions) + 1
            cleaned_en_questions.append({
                'order_num': order,
                'question_text': q_text.strip(),
                'options': [str(opt).strip() for opt in options[:4]],
                'correct_answer': str(correct_answer).strip(),
                'hint': str(hint).strip() if hint else None
            })

            if has_hi and hi_q:
                hi_opts = [str(o).strip() for o in hi_q.get('options', [])[:4]]
                hi_corr = str(hi_q.get('correct_answer', '')).strip()
                if hi_corr not in hi_opts and hi_opts:
                    hi_corr = hi_opts[0]
                cleaned_hi_questions.append({
                    'order_num': order,
                    'question_text': str(hi_q.get('question_text', '')).strip(),
                    'options': hi_opts,
                    'correct_answer': hi_corr,
                    'hint': str(hi_q.get('hint', '')).strip() if hi_q.get('hint') else None
                })
        else:
            logger.warning(f"Question failed compliance check: {reason}. Attempting retry...")
            # Retry up to 2 times
            retry_success = False
            for retry_attempt in range(1, 3):
                fallback_data = _generate_grounded_fallback(
                    category_name, age_band_key, 'Easy', is_translation_gap=has_hi
                )
                alt_bank = fallback_data['questions']
                replacement_q = alt_bank[(idx + retry_attempt) % len(alt_bank)]

                r_safe, _ = compliance_agent.check_text(replacement_q['question_text'])
                if has_hi and 'translations' in fallback_data:
                    hi_alt_bank = fallback_data['translations']['hi']['questions']
                    replacement_hi_q = hi_alt_bank[(idx + retry_attempt) % len(hi_alt_bank)]
                    hi_r_safe, _ = compliance_agent.check_text(replacement_hi_q['question_text'])
                    r_safe = r_safe and hi_r_safe
                else:
                    replacement_hi_q = None

                if r_safe:
                    order = len(cleaned_en_questions) + 1
                    cleaned_en_questions.append({
                        'order_num': order,
                        'question_text': replacement_q['question_text'],
                        'options': replacement_q['options'],
                        'correct_answer': replacement_q['correct_answer'],
                        'hint': replacement_q.get('hint')
                    })
                    if has_hi and replacement_hi_q:
                        cleaned_hi_questions.append({
                            'order_num': order,
                            'question_text': replacement_hi_q['question_text'],
                            'options': replacement_hi_q['options'],
                            'correct_answer': replacement_hi_q['correct_answer'],
                            'hint': replacement_hi_q.get('hint')
                        })
                    retry_success = True
                    break

            if not retry_success:
                logger.warning(f"Discarded question {idx+1} after failing 2 compliance retries.")
                discarded_count += 1

    if raw_hi_questions is not None:
        return cleaned_en_questions, cleaned_hi_questions, discarded_count
    return cleaned_en_questions, discarded_count


# =============================================================================
# 5. HIGH-LEVEL DRAFT GENERATOR ENTRY POINT
# =============================================================================

def generate_draft_activity(
    category_id: int,
    age_band: str,
    difficulty: str,
    custom_guidance: str = None,
    suggestion_id: int = None
) -> dict:
    """
    Main entry point for AI content drafting.
    1. Collects real platform context & builds prompt
    2. Calls Anthropic API (or grounded offline fallback)
    3. Enforces dual-language compliance verification (EN & HI) with retry/discard loop
    4. Packages draft payload with full grounding transparency metadata
    """
    band_key = age_band if age_band in AGE_BANDS else '6-9'
    band_info = AGE_BANDS[band_key]
    category = db.session.get(Category, category_id)
    category_name = category.name if category else 'General Learning'

    sugg_context = get_suggestion_context(suggestion_id)
    is_translation_gap = bool(
        sugg_context and sugg_context.get('suggestion_type') == ContentSuggestion.TYPE_TRANSLATION_GAP
    )

    system_prompt, user_prompt, platform_context_meta = build_generation_prompt(
        category_id=category_id,
        age_band_key=band_key,
        difficulty=difficulty,
        custom_guidance=custom_guidance,
        suggestion_id=suggestion_id
    )

    raw_draft = None
    has_api_key = bool(os.environ.get('ANTHROPIC_API_KEY'))

    if has_api_key:
        try:
            logger.info(f"Calling Anthropic API for category {category_name}, age band {band_key}")
            raw_draft = _call_anthropic_api(system_prompt, user_prompt)
        except Exception as e:
            logger.warning(f"Anthropic API call failed ({e}). Falling back to grounded generator.")
            raw_draft = None

    if not raw_draft:
        raw_draft = _generate_grounded_fallback(
            category_name=category_name,
            age_band_key=band_key,
            difficulty=difficulty,
            suggestion_context=sugg_context,
            custom_guidance=custom_guidance,
            is_translation_gap=is_translation_gap
        )

    # Clean English title and description with compliance check
    title = raw_draft.get('title', 'Playful Learning Adventure').strip()
    is_title_safe, _ = compliance_agent.check_text(title)
    if not is_title_safe:
        title = f"{category_name} Learning Discovery"

    description = raw_draft.get('description', '').strip()
    is_desc_safe, _ = compliance_agent.check_text(description)
    if not is_desc_safe:
        description = f"An engaging {category_name.lower()} activity designed to reinforce core cognitive skills."

    # Extract raw Hindi translations if present
    raw_translations = raw_draft.get('translations', {})
    raw_hi = raw_translations.get('hi', {}) if isinstance(raw_translations, dict) else {}
    raw_hi_questions = raw_hi.get('questions', []) if isinstance(raw_hi, dict) else []

    # Verify and clean questions with compliance check & retry loop
    raw_questions = raw_draft.get('questions', [])
    if is_translation_gap or raw_hi:
        clean_questions, clean_hi_questions, discarded_count = verify_and_clean_questions(
            raw_questions, category_name, band_key, raw_hi_questions=raw_hi_questions
        )
    else:
        clean_questions, discarded_count = verify_and_clean_questions(
            raw_questions, category_name, band_key
        )
        clean_hi_questions = []

    # Clean Hindi title and description if dual-language
    final_translations = None
    has_hindi = False

    if is_translation_gap or raw_hi:
        hi_title = raw_hi.get('title', '').strip() if isinstance(raw_hi, dict) else ''
        if not hi_title:
            category_names_hi = {
                'Visual Learning': 'दृश्य अधिगम',
                'Logic': 'तर्क शक्ति',
                'Numbers': 'संख्या ज्ञान',
                'Language': 'भाषा ज्ञान',
                'Memory': 'स्मृति अभ्यास'
            }
            hi_title = f"{category_names_hi.get(category_name, 'रोमांचक')} खोज यात्रा ({difficulty})"

        is_hi_title_safe, _ = compliance_agent.check_text(hi_title)
        if not is_hi_title_safe:
            hi_title = "रोमांचक खोज यात्रा"

        hi_desc = raw_hi.get('description', '').strip() if isinstance(raw_hi, dict) else ''
        if not hi_desc:
            hi_desc = f"{band_info['min_age']}-{band_info['max_age']} वर्ष के बच्चों के लिए सीखने की मजेदार गतिविधि।"

        is_hi_desc_safe, _ = compliance_agent.check_text(hi_desc)
        if not is_hi_desc_safe:
            hi_desc = "सीखने और नए कौशल विकसित करने की मजेदार गतिविधि।"

        final_translations = {
            'hi': {
                'title': hi_title,
                'description': hi_desc,
                'questions': clean_hi_questions
            }
        }
        has_hindi = True

    platform_context_meta['discarded_questions_count'] = discarded_count
    platform_context_meta['prompt_preview'] = {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt
    }
    platform_context_meta['is_translation_gap'] = is_translation_gap

    return {
        'title': title,
        'description': description,
        'category_id': category_id,
        'category_name': category_name,
        'difficulty': difficulty,
        'age_band': band_key,
        'min_age': band_info['min_age'],
        'max_age': band_info['max_age'],
        'estimated_duration': int(raw_draft.get('estimated_duration', band_info['default_duration'])),
        'suggestion_id': suggestion_id,
        'custom_guidance': custom_guidance,
        'questions': clean_questions,
        'translations': final_translations,
        'has_hindi': has_hindi,
        'platform_context': platform_context_meta
    }

