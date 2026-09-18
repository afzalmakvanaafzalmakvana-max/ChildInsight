from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, StringField, TextAreaField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class AssignTeacherForm(FlaskForm):
    """Form to pair a teacher with a student."""
    teacher_id = SelectField('Select Educator / Teacher', coerce=int, validators=[DataRequired()])
    child_id = SelectField('Select Student / Child', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Student')


class ChangeRoleForm(FlaskForm):
    """Form to update a user's system role."""
    role = SelectField(
        'New Role',
        choices=[
            ('parent', 'Parent / Guardian'),
            ('teacher', 'Educator / Teacher'),
            ('admin', 'Administrator')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Update Role')


class CategoryForm(FlaskForm):
    """Form to create or edit an activity category."""
    name = StringField('Category Name (English)', validators=[
        DataRequired(message="Category name is required."),
        Length(min=2, max=100, message="Category name must be between 2 and 100 characters.")
    ])
    description = TextAreaField('Description (English)', validators=[
        Optional(),
        Length(max=500, message="Description cannot exceed 500 characters.")
    ])
    icon = StringField('Icon / Emoji', validators=[
        Optional(),
        Length(max=50, message="Icon cannot exceed 50 characters.")
    ])
    name_hi = StringField('Category Name (Hindi — optional)', validators=[
        Optional(),
        Length(max=100, message="Hindi category name cannot exceed 100 characters.")
    ])
    description_hi = TextAreaField('Description (Hindi — optional)', validators=[
        Optional(),
        Length(max=500, message="Hindi description cannot exceed 500 characters.")
    ])
    submit = SubmitField('Save Category')


class ActivityForm(FlaskForm):
    """Form to create or edit an educational activity."""
    title = StringField('Activity Title (English)', validators=[
        DataRequired(message="Activity title is required."),
        Length(min=2, max=150, message="Title must be between 2 and 150 characters.")
    ])
    description = TextAreaField('Description / Instructions (English)', validators=[
        Optional(),
        Length(max=1000, message="Description cannot exceed 1000 characters.")
    ])
    title_hi = StringField('Activity Title (Hindi — optional)', validators=[
        Optional(),
        Length(max=150, message="Hindi title cannot exceed 150 characters.")
    ])
    description_hi = TextAreaField('Description / Instructions (Hindi — optional)', validators=[
        Optional(),
        Length(max=1000, message="Hindi description cannot exceed 1000 characters.")
    ])
    category_id = SelectField('Category', coerce=int, validators=[
        DataRequired(message="Please select a category.")
    ])
    difficulty = SelectField('Difficulty Level', choices=[
        ('Beginner', 'Beginner'),
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Advanced', 'Advanced')
    ], default='Easy', validators=[DataRequired()])
    estimated_duration = IntegerField('Estimated Duration (minutes)', default=5, validators=[
        DataRequired(message="Duration is required."),
        NumberRange(min=1, max=60, message="Duration must be between 1 and 60 minutes.")
    ])
    min_age = IntegerField('Minimum Target Age', default=4, validators=[
        DataRequired(message="Minimum age is required."),
        NumberRange(min=3, max=18, message="Minimum age must be between 3 and 18.")
    ])
    max_age = IntegerField('Maximum Target Age', default=14, validators=[
        DataRequired(message="Maximum age is required."),
        NumberRange(min=3, max=18, message="Maximum age must be between 3 and 18.")
    ])
    is_active = BooleanField('Active (available to children in activity picker)', default=True)
    submit = SubmitField('Save Activity')


class QuestionForm(FlaskForm):
    """Form to create or edit an activity question."""
    question_text = TextAreaField('Question Prompt / Text (English)', validators=[
        DataRequired(message="Question prompt is required."),
        Length(min=2, max=1000, message="Question prompt must be between 2 and 1000 characters.")
    ])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('matching', 'Visual Matching'),
        ('counting', 'Counting'),
        ('sequence', 'Pattern / Sequence'),
        ('word_puzzle', 'Word Puzzle / Clue')
    ], default='multiple_choice', validators=[DataRequired()])
    options = TextAreaField('Choices / Options (English — one option per line)', validators=[
        DataRequired(message="At least two choices are required.")
    ])
    correct_answer = StringField('Correct Answer (English — must match one choice)', validators=[
        DataRequired(message="Correct answer is required."),
        Length(max=255, message="Correct answer cannot exceed 255 characters.")
    ])
    hint = StringField('Encouraging Hint (English — optional)', validators=[
        Optional(),
        Length(max=255, message="Hint cannot exceed 255 characters.")
    ])
    question_text_hi = TextAreaField('Question Prompt / Text (Hindi — optional)', validators=[
        Optional(),
        Length(max=1000, message="Hindi question prompt cannot exceed 1000 characters.")
    ])
    options_hi = TextAreaField('Choices / Options (Hindi — optional, one option per line)', validators=[
        Optional()
    ])
    correct_answer_hi = StringField('Correct Answer (Hindi — optional)', validators=[
        Optional(),
        Length(max=255, message="Hindi correct answer cannot exceed 255 characters.")
    ])
    hint_hi = StringField('Encouraging Hint (Hindi — optional)', validators=[
        Optional(),
        Length(max=255, message="Hindi hint cannot exceed 255 characters.")
    ])
    order_num = IntegerField('Question Order #', default=1, validators=[
        DataRequired(message="Question order number is required."),
        NumberRange(min=1, max=100, message="Order must be between 1 and 100.")
    ])
    submit = SubmitField('Save Question')
