from hashlib import md5
import uuid
from datetime import datetime
from hashlib import md5
from time import time
import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SelectField, RadioField
from wtforms.validators import DataRequired
from app import db, login

study_user = db.Table('study_user',
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                      db.Column('study_id', db.Integer, db.ForeignKey('study.id'))
                      )

researchmodel_corevariable = db.Table('researchmodel_corevariable',
                                      db.Column('researchmodel_id', db.Integer, db.ForeignKey('researchmodel.id')),
                                      db.Column('corevariable_id', db.Integer, db.ForeignKey('corevariable.id'))
                                      )

questionnaire_demographic = db.Table('questionnaire_demographic',
                                     db.Column('questionnaire_id', db.Integer, db.ForeignKey('questionnaire.id')),
                                     db.Column('demographic_id', db.Integer, db.ForeignKey('demographic.id'))
                                     )



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(90), unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(250))

    linked_studies = db.relationship('Study', secondary=study_user, backref=db.backref('researchers'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def link(self, study):
        if not self.is_linked(study):
            self.linked_studies.append(study)

    def unlink(self, study):
        if self.is_linked(study):
            self.linked_studies.remove(study)

    def is_linked(self, study):
        return self.linked_studies.filter(
            study_user.c.study_id == study.id).count() > 0

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Study(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    description = db.Column(db.String(5000))
    technology = db.Column(db.String(100))
    code = db.Column(db.String(60), unique=True)
    stage_1 = db.Column(db.Boolean, default=True)
    stage_2 = db.Column(db.Boolean, default=False)
    stage_3 = db.Column(db.Boolean, default=False)
    stage_completed = db.Column(db.Boolean, default=False)

    linked_users = db.relationship('User', secondary=study_user, backref=db.backref('researchers'), lazy='dynamic')

    def __repr__(self):
        return '<Study {}>'.format(self.name_study)

    def change_model(self, new_model_id):
        self.model_id = new_model_id

    def create_code(self):
        self.code = str(uuid.uuid4())


class ResearchModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    linked_corevariables = db.relationship('CoreVariable', secondary=researchmodel_corevariable,
                                           backref=db.backref('corevariables'), lazy='dynamic')


class CoreVariable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    abbreviation = db.Column(db.String(4))
    description = db.Column(db.String(800))


class Relation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('utau_tmodel.id'))
    influencer_id = db.Column(db.Integer, db.ForeignKey('core_variable.id'))
    influenced_id = db.Column(db.Integer, db.ForeignKey('core_variable.id'))

    def return_relation(self):
        return '{} ----> {}'.format(
            CoreVariable.query.get(self.influencer_id).name,
            CoreVariable.query.get(self.influenced_id).name)


class Questionnaire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True)
    scale = db.Column(db.Integer)

    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    linked_questiongroups = db.relationship('QuestionGroup', backref='questionnaire_questiongroup',
                                            lazy='dynamic')

    def __repr__(self):
        return '<Questionnaire {}>'.format(self.name)

    def total_completed_cases(self):
        total = Case.query.filter_by(questionnaire_id=self.id, completed=True).count()
        return str(total)


class QuestionGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaire.id'))
    corevariable_id = db.Column(db.Integer, db.ForeignKey('core_variable.id'))

    def __repr__(self):
        return '<Question group {}>'.format(self.title)


class Demographic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(300))
    optional = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return '<Demographic {}>'.format(self.name)

    def return_field(self):
        if self.questiontype_name == "open":
            if self.optional:
                return StringField(self.name)
            required_name = self.name + '*'
            return StringField(required_name, validators=[DataRequired()])
        elif self.questiontype_name == "multiplechoice":
            if self.optional:
                choices = self.choices.split(',')
                choices.append("No Answer")
                return SelectField(u'{}'.format(self.name), choices=choices)
            required_name = self.name + '*'
            return SelectField(u'{}'.format(required_name), choices=self.choices.split(','))
        elif self.questiontype_name == "radio":
            if self.optional:
                choices = self.choices.split(',')
                choices.append("No Answer")
                return RadioField(u'{}'.format(self.name), choices=choices)
            required_name = self.name + '*'
            return RadioField(u'{}'.format(required_name), choices=self.choices.split(','))


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(120))
    reversed_score = db.Column(db.Boolean, default=False)
    question_code = db.Column(db.String(10))
    questiongroup_id = db.Column(db.Integer, db.ForeignKey('question_group.id'))

    def __repr__(self):
        return '<Question {}>'.format(self.question)


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session = db.Column(db.String(100), unique=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow())
    completed = db.Column(db.Boolean, default=False)


class QuestionAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.SmallInteger)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))


class DemographicAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer = db.Column(db.String(200))
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    demographic_id = db.Column(db.Integer, db.ForeignKey('demographic.id'))
