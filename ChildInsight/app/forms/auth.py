import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Regexp, Length, EqualTo, ValidationError
from app.models.user import User

# Permissive email regex accepting standard domains and development/internal TLDs (e.g. .local, .test)
EMAIL_VALIDATOR = Regexp(
    r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
    message="Please enter a valid email address."
)


class RegisterForm(FlaskForm):
    """Registration form with client- and server-side validation."""
    name = StringField(
        'Full Name',
        validators=[DataRequired(message="Name is required."), Length(min=2, max=100)]
    )
    email = StringField(
        'Email Address',
        validators=[DataRequired(message="Email is required."), EMAIL_VALIDATOR, Length(max=120)]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required."),
            Length(min=6, max=128, message="Password must be at least 6 characters.")
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo('password', message="Passwords must match.")
        ]
    )
    role = SelectField(
        'I am registering as',
        choices=[
            ('parent', 'Parent / Guardian'),
            ('teacher', 'Educator / Teacher')
        ],
        default='parent',
        validators=[DataRequired()]
    )
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        """Ensure email is unique across the system."""
        normalized_email = field.data.strip().lower()
        if User.query.filter_by(email=normalized_email).first():
            raise ValidationError('An account with this email address already exists.')


class LoginForm(FlaskForm):
    """Login form supporting persistent session toggle and next redirect."""
    email = StringField(
        'Email Address',
        validators=[DataRequired(message="Email is required."), EMAIL_VALIDATOR]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message="Password is required.")]
    )
    remember_me = BooleanField('Keep me signed in')
    next = HiddenField('next')
    submit = SubmitField('Sign In')


class ForgotPasswordRequestForm(FlaskForm):
    """Form to initiate a password reset request via email."""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message="Email is required."),
            EMAIL_VALIDATOR
        ]
    )
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Form to set a new password using a validated reset token."""
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message="New password is required."),
            Length(min=6, max=128, message="Password must be at least 6 characters.")
        ]
    )
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo('password', message="Passwords must match.")
        ]
    )
    submit = SubmitField('Update Password')
