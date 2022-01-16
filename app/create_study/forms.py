from flask_wtf import FlaskForm
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, IntegerField, RadioField, BooleanField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User


class CreateNewStudyForm(FlaskForm):
    style_name = {'style': 'width:175%;'}
    name_of_study = StringField('Name of the study (max. 200 characters)',
                                validators=[DataRequired(), Length(min=0, max=200)], render_kw=style_name)
    style_description = {'style': 'width:250%;', "rows": 20}
    description_of_study = TextAreaField('Description of the study (max. 3000 characters)',
                                         validators=[DataRequired(), Length(min=0, max=3000)],
                                         render_kw=style_description)
    technology_of_study = StringField('Relevant technology of the study (max. 75 characters)',
                                      validators=[DataRequired(), Length(min=0, max=75)])
    submit = SubmitField('Create Study')


class EditStudyForm(FlaskForm):
    style_name = {'style': 'width:175%;'}
    name_of_study = StringField('Name of the study (max. 200 characters)',
                                validators=[DataRequired(), Length(min=0, max=200)], render_kw=style_name)
    style_description = {'style': 'width:250%;', "rows": 20}
    description_of_study = TextAreaField('Description of the study (max. 3000 characters)',
                                         validators=[DataRequired(), Length(min=0, max=3000)],
                                         render_kw=style_description)
    technology_of_study = StringField('Relevant technology of the study (max. 75 letters)',
                                      validators=[DataRequired(), Length(min=0, max=75)])
    submit = SubmitField('Edit Study')

    def __init__(self, original_name, original_description, original_technology, *args, **kwargs):
        super(EditStudyForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        self.original_description = original_description
        self.original_technology = original_technology


class CreateNewCoreVariableForm(FlaskForm):
    name_corevariable = StringField('Name of the core variable', validators=[DataRequired(), Length(min=0, max=50)])
    abbreviation_corevariable = StringField('The abbreviation of the core variable', validators=[DataRequired(),
                                                                                                 Length(min=0, max=4)])
    description_corevariable = TextAreaField('The description of the core variable',
                                             validators=[Length(min=0, max=800)])
    submit = SubmitField('Create Core Variable')


class CreateNewRelationForm(FlaskForm):
    abbreviation_influencer = SelectField(u'Influencer (relation goes from)') #StringField('The abbreviation of the influencer',
                                          #validators=[DataRequired(), Length(min=0, max=4)])
    abbreviation_influenced = SelectField(u'Influenced (relation goes to)')
    submit = SubmitField('Create Relation')
