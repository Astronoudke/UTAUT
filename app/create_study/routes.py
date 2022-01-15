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
from app.create_study.forms import CreateNewStudyForm, EditStudyForm
from app.main.functions import security_and_studycheck
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from app.models import Study, CoreVariable, Relation, ResearchModel


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
        return redirect(url_for('create_study.utaut', study_code=study.code))
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


@bp.route('/utaut/new_corevariable/<study_code>', methods=['GET', 'POST'])
@login_required
def new_corevariable(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    # De Form voor het aanmaken van een nieuwe kernvariabele.
    study = Study.query.filter_by(code=study_code).first()
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
        model = UTAUTmodel.query.filter_by(id=study.model_id).first()
        new_corevariable.link(model)
        db.session.commit()

        return redirect(url_for('new_study.utaut', study_code=study_code))

    return render_template("new_study/new_corevariable.html", title='New Core Variable', form=form)