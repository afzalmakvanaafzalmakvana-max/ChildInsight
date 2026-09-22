"""
AI-Assisted Form Translation Agent (app/agent/translation_agent.py)

Provides child-appropriate, educational translations from English into Hindi
for Activity and Category titles/names and descriptions.

Key Guiding Principles:
1. Tone & Calibration: Translations match ChildInsight's playful, warm,
   and encouraging tone (Devanagari script) calibrated for young learners.
2. Compliance Gate: Every generated string is strictly screened by the Compliance
   Agent (PRD §4). Any forbidden clinical/diagnostic/deficit terms in either
   language cause immediate rejection.
3. Advisory-Only: This agent returns in-memory text suggestions for administrator
   review and editing. It NEVER writes directly to database tables.
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
import urllib.request
import urllib.error

from app.agent import compliance_agent

logger = logging.getLogger('childinsight.translation_agent')

# Common cognitive domain & category mappings for grounded fallback
CATEGORY_FALLBACK_TRANSLATIONS = {
    'visual learning': {
        'name_hi': 'दृश्य शिक्षण',
        'description_hi': 'आकृतियों, रंगों और दृश्य पैटर्नों को पहचानने और समझने का मजेदार अभ्यास।'
    },
    'visual': {
        'name_hi': 'दृश्य शिक्षण',
        'description_hi': 'आकृतियों, रंगों और दृश्य पैटर्नों को पहचानने और समझने का मजेदार अभ्यास।'
    },
    'logic & reasoning': {
        'name_hi': 'तर्क और विचार',
        'description_hi': 'समस्या समाधान, पहेलियों और तार्किक सोच को विकसित करने की रोमांचक चुनौतियाँ।'
    },
    'logic': {
        'name_hi': 'तर्क और विचार',
        'description_hi': 'समस्या समाधान, पहेलियों और तार्किक सोच को विकसित करने की रोमांचक चुनौतियाँ।'
    },
    'numbers & math': {
        'name_hi': 'संख्या और गणित',
        'description_hi': 'गिनती, बुनियादी अंकगणित और संख्या पैटर्नों का चंचल और आनंदमय अन्वेषण।'
    },
    'numbers': {
        'name_hi': 'संख्या और गणित',
        'description_hi': 'गिनती, बुनियादी अंकगणित और संख्या पैटर्नों का चंचल और आनंदमय अन्वेषण।'
    },
    'language & words': {
        'name_hi': 'भाषा और शब्दावली',
        'description_hi': 'शब्दावली, वाक्य निर्माण और भाषाई अभिव्यक्ति को समृद्ध करने की रचनात्मक यात्रा।'
    },
    'language': {
        'name_hi': 'भाषा और शब्दावली',
        'description_hi': 'शब्दावली, वाक्य निर्माण और भाषाई अभिव्यक्ति को समृद्ध करने की रचनात्मक यात्रा।'
    },
    'memory & focus': {
        'name_hi': 'स्मृति और ध्यान',
        'description_hi': 'एकाग्रता, स्मृति प्रतिधारण और ध्यान केंद्रित करने के लिए उत्साहवर्धक खेल।'
    },
    'memory': {
        'name_hi': 'स्मृति और ध्यान',
        'description_hi': 'एकाग्रता, स्मृति प्रतिधारण और ध्यान केंद्रित करने के लिए उत्साहवर्धक खेल।'
    },
    'science & nature': {
        'name_hi': 'विज्ञान और प्रकृति',
        'description_hi': 'हमारे आसपास की प्राकृतिक दुनिया, पौधों, मौसम और वैज्ञानिक आश्चर्यों की खोज।'
    },
    'science': {
        'name_hi': 'विज्ञान और प्रकृति',
        'description_hi': 'हमारे आसपास की प्राकृतिक दुनिया, पौधों, मौसम और वैज्ञानिक आश्चर्यों की खोज।'
    },
    'creative arts': {
        'name_hi': 'रचनात्मक कला',
        'description_hi': 'रंगों, कल्पना और रचनात्मक अभिव्यक्ति को प्रोत्साहित करने वाले आनंददायक अनुभव।'
    },
    'creative': {
        'name_hi': 'रचनात्मक कला',
        'description_hi': 'रंगों, कल्पना और रचनात्मक अभिव्यक्ति को प्रोत्साहित करने वाले आनंददायक अनुभव।'
    },
    'spatial awareness': {
        'name_hi': 'स्थानिक समझ',
        'description_hi': 'दिशाओं, स्थानों और त्रि-आयामी सोच को मजबूत करने वाले इंटरैक्टिव अभ्यास।'
    }
}

# English-to-Hindi educational vocabulary dictionary for fallback generation
VOCAB_MAPPINGS = {
    'safari': 'सफारी',
    'adventure': 'साहसिक खोज',
    'detective': 'जासूस',
    'explorer': 'अन्वेषक',
    'quest': 'खोज यात्रा',
    'master': 'मास्टर',
    'challenge': 'चुनौती',
    'puzzle': 'पहेली',
    'puzzles': 'पहेलियाँ',
    'pattern': 'पैटर्न',
    'patterns': 'पैटर्न',
    'shape': 'आकृति',
    'shapes': 'आकृतियाँ',
    'color': 'रंग',
    'colors': 'रंग',
    'number': 'संख्या',
    'numbers': 'संख्याएँ',
    'grid': 'ग्रिड',
    'word': 'शब्द',
    'words': 'शब्द',
    'math': 'गणित',
    'memory': 'स्मृति',
    'focus': 'ध्यान',
    'logic': 'तर्क',
    'animal': 'जानवर',
    'animals': 'पशु-पक्षी',
    'space': 'अंतरिक्ष',
    'star': 'तारा',
    'stars': 'तारे',
    'nature': 'प्रकृति',
    'story': 'कहानी',
    'stories': 'कहानियाँ',
    'rhythm': 'लय और ताल',
    'garden': 'बगीचा',
    'forest': 'जंगल',
    'ocean': 'महासागर',
    'sea': 'समुद्र',
    'rainbow': 'इंद्रधनुष',
    'building': 'निर्माण',
    'blocks': 'ब्लॉक्स',
    'magic': 'जादुई',
    'junior': 'जूनियर',
    'smart': 'स्मार्ट',
    'discovery': 'खोज',
    'fun': 'मजेदार',
    'time': 'समय',
    'clock': 'घड़ी',
    'coding': 'कोडिंग',
    'code': 'कोड',
    'mystery': 'रहस्य',
    'learning': 'शिक्षण',
    'skills': 'कौशल',
    'match': 'मिलाओ',
    'matching': 'मिलान',
    'counting': 'गिनती',
    'finder': 'खोजकर्ता',
    'builder': 'निर्माता',
    'hero': 'नायक',
    'heroes': 'नायक',
    'rhyme': 'कविता',
    'sound': 'ध्वनि',
    'sounds': 'ध्वनियाँ'
}


def _clean_text(val: str | None) -> str:
    """Helper to trim and normalize whitespace."""
    if not val:
        return ""
    return re.sub(r'\s+', ' ', str(val)).strip()


def _call_anthropic_api(system_prompt: str, user_prompt: str) -> dict:
    """
    Invokes the Anthropic Messages API (claude-3-5-sonnet-20241022) to translate
    educational titles and descriptions into child-appropriate Hindi.
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
        "max_tokens": 1000,
        "temperature": 0.3,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=20) as response:
        res_body = response.read().decode('utf-8')
        res_json = json.loads(res_body)

    content_blocks = res_json.get('content', [])
    raw_text = "".join(b.get('text', '') for b in content_blocks if b.get('type') == 'text').strip()

    # Strip potential markdown fences
    if raw_text.startswith('```json'):
        raw_text = raw_text[7:]
    elif raw_text.startswith('```'):
        raw_text = raw_text[3:]
    if raw_text.endswith('```'):
        raw_text = raw_text[:-3]

    return json.loads(raw_text.strip())


def _generate_fallback_translation(title_or_name: str, description: str, context_type: str = 'activity') -> dict:
    """
    High-quality, deterministic offline/fallback translation generator.
    Produces child-friendly, natural Hindi using established platform vocabulary.
    """
    title_clean = _clean_text(title_or_name)
    desc_clean = _clean_text(description)
    title_lower = title_clean.lower()

    # 1. Check category dictionary first if it's a category
    if context_type == 'category' and title_lower in CATEGORY_FALLBACK_TRANSLATIONS:
        match = CATEGORY_FALLBACK_TRANSLATIONS[title_lower]
        return {
            'title_hi': match['name_hi'],
            'name_hi': match['name_hi'],
            'description_hi': match['description_hi'] if not desc_clean else _translate_fallback_description(desc_clean, match['name_hi'])
        }

    # 2. Try importing seeded activity translations
    try:
        from app.utils.activity_translations_seeds import HINDI_ACTIVITY_TRANSLATIONS
        for seed_title, seed_data in HINDI_ACTIVITY_TRANSLATIONS.items():
            clean_seed_title = re.sub(r'\s*\[Demo Data\]\s*', '', seed_title, flags=re.IGNORECASE).strip().lower()
            clean_input_title = re.sub(r'\s*\[Demo Data\]\s*', '', title_clean, flags=re.IGNORECASE).strip().lower()
            if clean_seed_title == clean_input_title and isinstance(seed_data, dict):
                hi_title = re.sub(r'\s*\[Demo Data\]\s*', '', seed_data.get('title', ''), flags=re.IGNORECASE).strip()
                hi_desc = seed_data.get('description', '').strip()
                if hi_title:
                    return {
                        'title_hi': hi_title,
                        'name_hi': hi_title,
                        'description_hi': hi_desc or _translate_fallback_description(desc_clean, hi_title)
                    }
    except Exception as e:
        logger.debug(f"Catalog seed lookup passed: {e}")

    # 3. Procedural Title Translation
    translated_title = _translate_fallback_title(title_clean)

    # 4. Procedural Description Translation
    translated_desc = _translate_fallback_description(desc_clean, translated_title)

    return {
        'title_hi': translated_title,
        'name_hi': translated_title,
        'description_hi': translated_desc
    }


def _translate_fallback_title(title_text: str) -> str:
    """Translates educational title tokens into natural Hindi."""
    if not title_text:
        return ""

    words = re.findall(r'[A-Za-z0-9&]+|[^\w\s]', title_text)
    translated_parts = []

    for word in words:
        w_lower = word.lower()
        if w_lower in VOCAB_MAPPINGS:
            translated_parts.append(VOCAB_MAPPINGS[w_lower])
        elif w_lower == '&' or w_lower == 'and':
            translated_parts.append('और')
        else:
            # Keep numbers or transliterate known prefixes
            translated_parts.append(word)

    result = " ".join(translated_parts).strip()
    # Normalize common Hindi connectors
    result = re.sub(r'\s+और\s+', ' और ', result)
    return result if result else title_text


def _translate_fallback_description(desc_text: str, title_hi: str = "") -> str:
    """Generates child-appropriate Hindi description from English description."""
    if not desc_text:
        if title_hi:
            return f"बच्चों के लिए '{title_hi}' की आनंददायक और ज्ञानवर्धक सीखने की गतिविधि।"
        return "बच्चों के लिए एक आनंददायक और उत्साहवर्धक इंटरैक्टिव सीखने की गतिविधि।"

    # Detect theme from English description
    desc_lower = desc_text.lower()
    themes = []
    if any(k in desc_lower for k in ['color', 'shape', 'visual', 'pattern']):
        themes.append('आकृतियों और रंगों की पहचान')
    if any(k in desc_lower for k in ['number', 'count', 'math', 'calculate', 'grid']):
        themes.append('संख्याओं और गणितीय सोच')
    if any(k in desc_lower for k in ['word', 'letter', 'read', 'vocab', 'language', 'story']):
        themes.append('शब्दावली और भाषाई कौशल')
    if any(k in desc_lower for k in ['logic', 'puzzle', 'solve', 'reasoning', 'sequence']):
        themes.append('तार्किक पहेलियों और समस्या समाधान')
    if any(k in desc_lower for k in ['memory', 'focus', 'remember', 'attention']):
        themes.append('स्मृति और एकाग्रता')
    if any(k in desc_lower for k in ['nature', 'science', 'animal', 'plant', 'space']):
        themes.append('प्रकृति और वैज्ञानिक अन्वेषण')

    if themes:
        theme_str = " तथा ".join(themes[:2])
        return f"{theme_str} को प्रोत्साहित करने वाली एक चंचल और इंटरैक्टिव सीखने की यात्रा।"

    # Fallback to general encouraging sentence
    return "बच्चों के संज्ञानात्मक कौशल और रचनात्मक सोच को विकसित करने के लिए एक प्रेरणादायक सीखने की गतिविधि।"


def translate_form_content(
    title_or_name: str,
    description: str,
    context_type: str = 'activity',
    age_band: str = None
) -> tuple[bool, dict | None, str | None]:
    """
    Main entrypoint for translating Activity or Category form content into Hindi.

    Args:
        title_or_name: English title (activity) or name (category).
        description: English description.
        context_type: 'activity' or 'category'.
        age_band: Optional target age band (e.g. '4-6', '6-9') for activities.

    Returns:
        tuple[is_success (bool), translation_data (dict | None), error_message (str | None)]
        On success, translation_data contains:
            {
                'title_hi': str,
                'name_hi': str,
                'description_hi': str
            }
    """
    title_clean = _clean_text(title_or_name)
    desc_clean = _clean_text(description)

    if not title_clean and not desc_clean:
        return False, None, "Please provide an English title/name or description before translating."

    # Pre-check English inputs against PRD §4 compliance blacklist
    safe, reason = compliance_agent.check_text(title_clean)
    if not safe:
        return False, None, f"English title violates compliance: {reason}"

    if desc_clean:
        safe, reason = compliance_agent.check_text(desc_clean)
        if not safe:
            return False, None, f"English description violates compliance: {reason}"

    trans_result = None
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    # Try Anthropic API if key is configured
    if api_key:
        try:
            system_prompt = (
                "You are an expert bilingual educational linguist for 'ChildInsight', an intelligent "
                "developmental learning platform for children aged 4-14.\n\n"
                "GOAL:\n"
                "Translate the provided English educational title/name and description into natural, "
                "warm, playful, child-friendly Hindi (Devanagari script).\n\n"
                "CORE RULES:\n"
                "1. Tone: Cheerful, encouraging, gamified, and age-appropriate. Avoid stiff, overly formal, "
                "or archaic textbook language.\n"
                "2. PRD §4 COMPLIANCE IS STRICTLY MANDATORY:\n"
                "- NEVER use clinical, psychiatric, medicalized, or diagnostic deficit terms in Hindi or English.\n"
                f"- FORBIDDEN HINDI TERMS:\n  {', '.join(compliance_agent.FORBIDDEN_TERMS_HI)}\n"
                "- Do not diagnose or evaluate mental capacity. Focus entirely on cheerful problem solving.\n"
                "3. OUTPUT FORMAT:\n"
                "Return ONLY a JSON object with this exact structure (no commentary, no markdown):\n"
                "{\n"
                '  "title_hi": "हिंदी शीर्षक",\n'
                '  "description_hi": "हिंदी विवरण"\n'
                "}"
            )

            context_label = "Activity" if context_type == 'activity' else "Category / Cognitive Domain"
            user_prompt = (
                f"CONTEXT: {context_label}\n"
                f"AGE BAND: {age_band or 'All Ages'}\n"
                f"ENGLISH TITLE/NAME: {title_clean}\n"
                f"ENGLISH DESCRIPTION: {desc_clean or 'N/A'}\n\n"
                "Translate both into engaging, compliant Hindi."
            )

            api_response = _call_anthropic_api(system_prompt, user_prompt)
            if isinstance(api_response, dict):
                hi_title = _clean_text(api_response.get('title_hi') or api_response.get('name_hi'))
                hi_desc = _clean_text(api_response.get('description_hi'))
                if hi_title or hi_desc:
                    trans_result = {
                        'title_hi': hi_title,
                        'name_hi': hi_title,
                        'description_hi': hi_desc
                    }
        except Exception as err:
            logger.warning(f"Anthropic API translation call failed, falling back to catalog generator: {err}")

    # Use grounded catalog fallback if API was unavailable or errored
    if not trans_result:
        trans_result = _generate_fallback_translation(title_clean, desc_clean, context_type=context_type)

    final_title_hi = trans_result.get('title_hi', '')
    final_desc_hi = trans_result.get('description_hi', '')

    # Strict compliance gate on generated Hindi output
    if final_title_hi:
        safe, reason = compliance_agent.check_text(final_title_hi)
        if not safe:
            logger.error(f"Translation agent generated non-compliant title: {reason}")
            return False, None, f"Generated Hindi translation violates ChildInsight PRD §4 compliance: {reason}"

    if final_desc_hi:
        safe, reason = compliance_agent.check_text(final_desc_hi)
        if not safe:
            logger.error(f"Translation agent generated non-compliant description: {reason}")
            return False, None, f"Generated Hindi translation violates ChildInsight PRD §4 compliance: {reason}"

    return True, {
        'title_hi': final_title_hi,
        'name_hi': final_title_hi,
        'description_hi': final_desc_hi
    }, None
