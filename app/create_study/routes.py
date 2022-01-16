from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
import numpy as np
import pandas as pd
import plspm.config as c
import json
from plspm.plspm import Plspm
from plspm.scheme import Scheme
from plspm.mode import Mode
from app import db
from app.create_study import bp
from app.create_study.forms import CreateNewStudyForm, EditStudyForm, CreateNewCoreVariableForm, CreateNewRelationForm
from app.main.functions import security_and_studycheck
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from app.models import User, Study, CoreVariable, Relation, ResearchModel


#############################################################################################################
#                                        De studie opzetten
#############################################################################################################


@bp.route('/new_study', methods=['GET', 'POST'])
@login_required
def new_study():
    # De Form voor het aanmaken van een nieuw onderzoek.
    form = CreateNewStudyForm()

    # Als de gebruiker aangeeft een nieuw onderzoek aan te willen maken
    if form.validate_on_submit():
        # Een nieuw onderzoek wordt opgezet.
        new_study = Study(name=form.name_of_study.data, description=form.description_of_study.data,
                          technology=form.technology_of_study.data)
        # Een unieke code wordt gegeven aan het onderzoek (gebruikmakend van UUID4).
        new_study.create_code()
        db.session.add(new_study)
        # De huidige gebruiker wordt gelinkt aan het onderzoek.
        current_user.link(new_study)
        db.session.commit()

        return redirect(url_for('create_study.choose_model', study_code=new_study.code))
    return render_template("create_study/new_study.html", title='New Study', form=form)


@bp.route('/edit_study/<study_code>', methods=['GET', 'POST'])
@login_required
def edit_study(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)
    study = Study.query.filter_by(code=study_code).first()

    # De Form voor het aanpassen van het onderzoek.
    form = EditStudyForm(study.name, study.description, study.technology)

    # Als de gebruiker aangeeft de onderzoek te willen aanpassen met de gegeven gegevens.
    if form.validate_on_submit():
        # De gegevens van de studie worden aangepast naar de ingegeven data binnen de Form.
        study.name = form.name_of_study.data
        study.description = form.description_of_study.data
        study.technology = form.technology_of_study.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('create_study.edit_model', study_code=study.code))
    # Als niks is ingegeven binnen de Form worden geen aanpassingen gemaakt (en dus gebruikgemaakt van de eigen
    # onderzoeksgegevens.
    elif request.method == 'GET':
        form.name_of_study.data = study.name
        form.description_of_study.data = study.description
        form.technology_of_study.data = study.technology
    return render_template('create_study/edit_study.html', title='Edit Profile',
                           form=form, study=study)


#############################################################################################################
#                                      Onderzoeksmodel opstellen
#############################################################################################################


@bp.route('/choose_model/<study_code>', methods=['GET', 'POST'])
@login_required
def choose_model(study_code):
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    models = ResearchModel.query.filter_by(user_id=current_user.id)
    amount_of_models = models.count()

    return render_template("create_study/choose_model.html", title='Choose model', study=study, models=models,
                           amount_of_models=amount_of_models)


@bp.route('/create_new_model/<study_code>', methods=['GET', 'POST'])
@login_required
def create_new_model(study_code):
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    if study.researchmodel_id is None:
        new_model = ResearchModel(name=study.name)
        db.session.add(new_model)
        db.session.commit()

        study.researchmodel_id = new_model.id
        db.session.commit()

    return redirect(url_for('create_study.edit_model', study_code=study.code))


@bp.route('/edit_model/<study_code>', methods=['GET', 'POST'])
@login_required
def edit_model(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)
    study = Study.query.filter_by(code=study_code).first()

    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    corevariables = [corevariable for corevariable in model.linked_corevariables]
    relations = [relation for relation in Relation.query.filter_by(model_id=model.id)]

    return render_template("create_study/edit_model.html", title='Edit model', study=study, model=model,
                           corevariables=corevariables, relations=relations)


@bp.route('/edit_model/new_corevariable/<study_code>', methods=['GET', 'POST'])
@login_required
def new_corevariable(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    corevariables = [corevariable for corevariable in CoreVariable.query.filter_by(user_id=current_user.id)]
    amount_of_corevariables = len(corevariables)

    return render_template("create_study/new_corevariable.html", title='New Core Variable', study=study, model=model,
                           corevariables=corevariables, amount_of_corevariables=amount_of_corevariables)


@bp.route('/add_corevariable/<study_code>/<corevariable_id>', methods=['GET', 'POST'])
@login_required
def add_corevariable(study_code, corevariable_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()

    corevariable.link(model)
    db.session.commit()

    return redirect(url_for('create_study.edit_model', study_code=study_code))


@bp.route('/edit_model/create_new_corevariable/<study_code>', methods=['GET', 'POST'])
@login_required
def create_new_corevariable(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    # De Form voor het aanmaken van een nieuwe kernvariabele.
    form = CreateNewCoreVariableForm()

    # Als de gebruiker aangeeft een nieuwe kernvariabele te willen aanmaken.
    if form.validate_on_submit():
        # De kernvariabele toegevoegd aan de database.
        new_corevariable = CoreVariable(name=form.name_corevariable.data,
                                        abbreviation=form.abbreviation_corevariable.data,
                                        description=form.description_corevariable.data,
                                        user_id=current_user.id)
        db.session.add(new_corevariable)
        db.session.commit()

        # De kernvariabele wordt binnen het onderzoeksmodel geplaatst.
        model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
        new_corevariable.link(model)
        db.session.commit()

        return redirect(url_for('create_study.edit_model', study_code=study_code))

    return render_template("create_study/create_new_corevariable.html", title='Create core variable', study=study,
                           form=form)


@bp.route('/remove_corevariable/<study_code>/<corevariable_id>', methods=['GET', 'POST'])
@login_required
def remove_corevariable(study_code, corevariable_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    # questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()

    # De kernvariabele uit het onderzoeksmodel halen en alle bijbehorende relaties verwijderen.
    corevariable.unlink(model)
    db.session.commit()
    Relation.query.filter_by(influencer_id=corevariable.id, model_id=model.id).delete()
    db.session.commit()
    Relation.query.filter_by(influenced_id=corevariable.id, model_id=model.id).delete()
    db.session.commit()

    # Als de kernvariabele al een vragenlijstgroep had binnen de vragenlijst deze en de bijbehorende vragen verwijderen.
    #if questionnaire:
    #    questiongroup = QuestionGroup.query.filter_by(title=corevariable.name,
    #                                                  questionnaire_id=questionnaire.id).first()
    #    Question.query.filter_by(questiongroup_id=questiongroup.id).delete()
    #    db.session.commit()
    #    QuestionGroup.query.filter_by(title=corevariable.name, questionnaire_id=questionnaire.id).delete()
    #    db.session.commit()

    return redirect(url_for('create_study.edit_model', study_code=study_code))


@bp.route('/utaut/new_relation/<study_code>', methods=['GET', 'POST'])
@login_required
def new_relation(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    # De Form voor het aanmaken van een nieuwe relatie.
    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()

    form = CreateNewRelationForm()
    form.abbreviation_influencer.choices = [(corevariable.id, corevariable.name) for corevariable in
                                            model.linked_corevariables]
    form.abbreviation_influenced.choices = [(corevariable.id, corevariable.name) for corevariable in
                                            model.linked_corevariables]

    # Als de gebruiker aangeeft een nieuwe relatie aan te willen maken.
    if form.validate_on_submit():
        # De ID van de beïnvloedende kernvariabele bepalen.
        id_influencer = [corevariable for corevariable in model.linked_corevariables if corevariable.abbreviation ==
                         form.abbreviation_influencer.data][0].id
        # De ID van de beïnvloede kernvariabele bepalen.
        id_influenced = [corevariable for corevariable in model.linked_corevariables if corevariable.abbreviation ==
                         form.abbreviation_influenced.data][0].id

        # De relatie aanmaken tussen de twee relevante kernvariabelen.
        newrelation = Relation(model_id=model.id,
                               influencer_id=id_influencer,
                               influenced_id=id_influenced)
        db.session.add(newrelation)
        db.session.commit()

        return redirect(url_for('create_study.edit_model', study_code=study_code))

    return render_template("create_study/new_relation.html", title='Create New Relation', form=form)


@bp.route('/remove_relation/<study_code>/<id_relation>', methods=['GET', 'POST'])
@login_required
def remove_relation(study_code, id_relation):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    # Het verwijderen van de relevante relatie.
    Relation.query.filter_by(id=id_relation).delete()
    db.session.commit()

    return redirect(url_for('create_study.edit_model', study_code=study_code))
