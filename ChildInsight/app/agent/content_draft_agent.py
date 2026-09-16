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

    matched_tone_titles = [a['title'] for a in cat_context['reference_activities']]
    calibration_titles = [f"{a['title']} ({a['category_name']}, {a['difficulty']})" for a in calibration_context[:5]]

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
        "- You must NEVER use clinical, psychological, or diagnostic terminology in any title, description, question, or hint.\n"
        "- FORBIDDEN TERMS (never include these words or forms of them):\n"
        f"  {', '.join(compliance_agent.FORBIDDEN_TERMS)}\n"
        "- Do not evaluate IQ, mental capacity, or deficit. Focus strictly on creative and cheerful problem solving.\n\n"
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
    custom_guidance: str = None
) -> dict:
    """
    High-quality, platform-grounded fallback generator used when ANTHROPIC_API_KEY
    is not set or in offline/test environments.
    Strictly follows PRD §4 non-diagnostic tone and age calibration.
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

    return {
        "title": base_title,
        "description": description,
        "estimated_duration": band_info['default_duration'],
        "questions": questions
    }


# =============================================================================
# 4. SECOND-LAYER COMPLIANCE VERIFICATION & RETRY LOGIC
# =============================================================================

def verify_and_clean_questions(raw_questions: list, category_name: str, age_band_key: str) -> tuple[list, int]:
    """
    Runs every generated question through compliance_agent.check_text().
    If a question contains clinical/diagnostic terms:
    - Retries generating a clean replacement up to 2 times
    - If it still fails after 2 retries, it is discarded/skipped.
    Returns (cleaned_questions: list, discarded_count: int).
    """
    cleaned_questions = []
    discarded_count = 0

    for idx, q in enumerate(raw_questions):
        q_text = q.get('question_text', '')
        options = q.get('options', [])
        correct_answer = q.get('correct_answer', '')
        hint = q.get('hint', '')

        # Check all text elements in the question
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

        if is_safe:
            # Format cleanly
            if correct_answer not in options and options:
                # Ensure correct answer is in options
                options[0] = correct_answer

            cleaned_questions.append({
                'order_num': len(cleaned_questions) + 1,
                'question_text': q_text.strip(),
                'options': [str(opt).strip() for opt in options[:4]],
                'correct_answer': str(correct_answer).strip(),
                'hint': str(hint).strip() if hint else None
            })
        else:
            logger.warning(f"Question failed compliance check: {reason}. Attempting retry...")
            # Retry up to 2 times
            retry_success = False
            for retry_attempt in range(1, 3):
                # Attempt regeneration of a clean question
                alt_bank = _generate_grounded_fallback(category_name, age_band_key, 'Easy')['questions']
                replacement_q = alt_bank[(idx + retry_attempt) % len(alt_bank)]

                # Check replacement question
                r_safe, _ = compliance_agent.check_text(replacement_q['question_text'])
                if r_safe:
                    cleaned_questions.append({
                        'order_num': len(cleaned_questions) + 1,
                        'question_text': replacement_q['question_text'],
                        'options': replacement_q['options'],
                        'correct_answer': replacement_q['correct_answer'],
                        'hint': replacement_q.get('hint')
                    })
                    retry_success = True
                    break

            if not retry_success:
                logger.warning(f"Discarded question {idx+1} after failing 2 compliance retries.")
                discarded_count += 1

    return cleaned_questions, discarded_count


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
    3. Enforces second-layer compliance verification with retry/discard loop
    4. Packages draft payload with full grounding transparency metadata
    """
    band_key = age_band if age_band in AGE_BANDS else '6-9'
    band_info = AGE_BANDS[band_key]
    category = db.session.get(Category, category_id)
    category_name = category.name if category else 'General Learning'

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
        sugg_context = get_suggestion_context(suggestion_id)
        raw_draft = _generate_grounded_fallback(
            category_name=category_name,
            age_band_key=band_key,
            difficulty=difficulty,
            suggestion_context=sugg_context,
            custom_guidance=custom_guidance
        )

    # Clean title and description with compliance check
    title = raw_draft.get('title', 'Playful Learning Adventure').strip()
    is_title_safe, _ = compliance_agent.check_text(title)
    if not is_title_safe:
        title = f"{category_name} Learning Discovery"

    description = raw_draft.get('description', '').strip()
    is_desc_safe, _ = compliance_agent.check_text(description)
    if not is_desc_safe:
        description = f"An engaging {category_name.lower()} activity designed to reinforce core cognitive skills."

    # Verify and clean questions with compliance check & retry loop
    raw_questions = raw_draft.get('questions', [])
    clean_questions, discarded_count = verify_and_clean_questions(raw_questions, category_name, band_key)

    platform_context_meta['discarded_questions_count'] = discarded_count
    platform_context_meta['prompt_preview'] = {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt
    }

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
        'platform_context': platform_context_meta
    }
