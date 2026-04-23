from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from data import db_session
from data.user import User

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Поле обязательно для заполнения"), 
        Email(message="Некорректный формат email")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(), 
        Length(min=6, message="Пароль должен быть не менее 6 символов")
    ])
    submit = SubmitField('Зарегистрироваться')


class EditProfileForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message="Некорректный email")])
    current_password = PasswordField('Текущий пароль')
    new_password = PasswordField('Новый пароль', validators=[Optional(), Length(min=6, message="Минимум 6 символов")])
    submit = SubmitField('Сохранить изменения')

    def validate_email(self, email):
        from flask import session
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email.data).first()
        if user and user.id != session.get("user_id"):
            raise ValidationError('Эта почта уже занята другим пользователем.')