import json
import random
from datetime import datetime, timezone
from app import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    translations_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    activities = db.relationship('Activity', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def translations(self) -> dict:
        if not self.translations_json:
            return {}
        try:
            return json.loads(self.translations_json)
        except Exception:
            return {}

    def get_name(self, lang: str = 'en') -> str:
        if lang == 'en' or not lang:
            return self.name
        hi_name = self.translations.get(lang, {}).get('name')
        if hi_name:
            return hi_name
        try:
            from app.translations import t
            return t(self.slug, default=self.name, lang=lang)
        except Exception:
            return self.name

    def get_description(self, lang: str = 'en') -> str:
        if lang == 'en' or not lang:
            return self.description or ''
        hi_desc = self.translations.get(lang, {}).get('description')
        if hi_desc:
            return hi_desc
        return self.description or ''

    def has_translation(self, lang: str = 'en') -> bool:
        if lang == 'en':
            return True
        return bool(self.translations.get(lang, {}).get('name'))

    def __repr__(self) -> str:
        return f'<Category id={self.id} name={self.name}>'


class Activity(db.Model):
    __tablename__ = 'activities'

    DIFFICULTIES = ('Beginner', 'Easy', 'Medium', 'Advanced')

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default='Easy')
    estimated_duration = db.Column(db.Integer, default=5)
    min_age = db.Column(db.Integer, default=4, nullable=False, index=True)
    max_age = db.Column(db.Integer, default=14, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_demo = db.Column(db.Boolean, default=True, nullable=False)
    translations_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    questions = db.relationship('ActivityQuestion', backref='activity', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def age_band(self) -> str:
        return f"{self.min_age}-{self.max_age}"

    @property
    def translations(self) -> dict:
        if not self.translations_json:
            return {}
        try:
            return json.loads(self.translations_json)
        except (ValueError, TypeError):
            return {}

    @translations.setter
    def translations(self, val: dict) -> None:
        self.translations_json = json.dumps(val, ensure_ascii=False)

    def get_title(self, lang: str = 'en') -> str:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            trans_title = self.translations[norm_lang].get('title')
            if trans_title:
                return trans_title
        return self.title

    def get_description(self, lang: str = 'en') -> str:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            trans_desc = self.translations[norm_lang].get('description')
            if trans_desc:
                return trans_desc
        return self.description or ''

    def has_translation(self, lang: str = 'en') -> bool:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang == 'en':
            return True
        return norm_lang in self.translations and bool(self.translations[norm_lang].get('title'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f'<Activity id={self.id} title={self.title} difficulty={self.difficulty} age={self.age_band}>'


class ActivityQuestion(db.Model):
    __tablename__ = 'activity_questions'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), default='multiple_choice', nullable=False)
    options_json = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    hint = db.Column(db.Text, nullable=True)
    order_num = db.Column(db.Integer, default=1, nullable=False)
    translations_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    @property
    def options(self):
        try:
            return json.loads(self.options_json)
        except (ValueError, TypeError):
            return []

    @property
    def shuffled_options(self):
        """Returns a randomized copy of options for display without mutating stored order."""
        opts = list(self.options)
        random.shuffle(opts)
        return opts

    @options.setter
    def options(self, val):
        self.options_json = json.dumps(val)

    @property
    def translations(self) -> dict:
        if not self.translations_json:
            return {}
        try:
            return json.loads(self.translations_json)
        except (ValueError, TypeError):
            return {}

    @translations.setter
    def translations(self, val: dict) -> None:
        self.translations_json = json.dumps(val, ensure_ascii=False)

    def get_question_text(self, lang: str = 'en') -> str:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            val = self.translations[norm_lang].get('question_text')
            if val:
                return val
        return self.question_text

    def get_prompt(self, lang: str = 'en') -> str:
        """Convenience alias for get_question_text."""
        return self.get_question_text(lang)

    def get_hint(self, lang: str = 'en') -> str | None:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            val = self.translations[norm_lang].get('hint')
            if val:
                return val
        return self.hint

    def get_options(self, lang: str = 'en') -> list:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            opts = self.translations[norm_lang].get('options')
            if opts and isinstance(opts, list):
                return opts
        return self.options

    def get_shuffled_options(self, lang: str = 'en') -> list:
        opts = list(self.get_options(lang))
        random.shuffle(opts)
        return opts

    def get_correct_answer(self, lang: str = 'en') -> str:
        from app.translations import normalize_language
        norm_lang = normalize_language(lang)
        if norm_lang != 'en' and norm_lang in self.translations:
            ans = self.translations[norm_lang].get('correct_answer')
            if ans:
                return ans
        return self.correct_answer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f'<ActivityQuestion id={self.id} activity_id={self.activity_id} order={self.order_num}>'
