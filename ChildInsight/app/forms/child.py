from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class ChildForm(FlaskForm):
    """Form to create or edit a child profile."""
    name = StringField(
        'Child Name',
        validators=[DataRequired(message="Name is required."), Length(min=2, max=100)]
    )
    age = IntegerField(
        'Age',
        validators=[
            Optional(),
            NumberRange(min=3, max=18, message="Age should be between 3 and 18.")
        ]
    )
    grade = SelectField(
        'Grade / Learning Stage',
        choices=[
            ('', '-- Select Grade / Stage --'),
            ('Preschool', 'Preschool / Nursery'),
            ('Kindergarten', 'Kindergarten'),
            ('1st Grade', '1st Grade'),
            ('2nd Grade', '2nd Grade'),
            ('3rd Grade', '3rd Grade'),
            ('4th Grade', '4th Grade'),
            ('5th Grade', '5th Grade'),
            ('6th Grade', '6th Grade'),
            ('7th Grade', '7th Grade'),
            ('8th Grade', '8th Grade'),
            ('9th Grade', '9th Grade'),
            ('10th Grade', '10th Grade'),
            ('11th Grade', '11th Grade'),
            ('12th Grade', '12th Grade'),
            ('Other', 'Other')
        ],
        validators=[Optional()],
        validate_choice=False
    )
    preferred_language = SelectField(
        'Preferred Language',
        choices=[
            ('English', 'English'),
            ('Hindi', 'Hindi'),
            ('Spanish', 'Spanish (Coming Soon)'),
            ('French', 'French (Coming Soon)'),
            ('German', 'German (Coming Soon)'),
            ('Mandarin', 'Mandarin (Coming Soon)')
        ],
        default='English'
    )
    submit = SubmitField('Save Profile')
