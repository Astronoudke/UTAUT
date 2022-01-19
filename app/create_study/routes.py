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
from app.create_study.forms import CreateNewStudyForm, EditStudyForm, CreateNewCoreVariableForm, CreateNewRelationForm, \
    CreateNewDemographicForm, CreateNewQuestionForm, EditQuestionForm, EditScaleForm
from app.create_study.functions import setup_questiongroups, setup_structure_dataframe, cronbachs_alpha, composite_reliability, \
    average_variance_extracted, heterotrait_monotrait, htmt_matrix, outer_vif_values_dict, return_questionlist_and_answerlist
from app.main.functions import security_and_studycheck
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from app.models import User, Study, CoreVariable, Relation, ResearchModel, Questionnaire, QuestionGroup, Question, \
    Demographic, DemographicOption, Case, DemographicAnswer


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
    models = [model for model in ResearchModel.query.filter_by(user_id=current_user.id)]
    print(models)
    amount_of_models = len(models)

    return render_template("create_study/choose_model.html", title='Choose model', study=study, models=models,
                           amount_of_models=amount_of_models)


@bp.route('/create_new_model/<study_code>', methods=['GET', 'POST'])
@login_required
def create_new_model(study_code):
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    if study.researchmodel_id is None:
        new_model = ResearchModel(name=study.name, user_id=current_user.id)
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
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()

    # De kernvariabele uit het onderzoeksmodel halen en alle bijbehorende relaties verwijderen.
    corevariable.unlink(model)
    db.session.commit()
    Relation.query.filter_by(influencer_id=corevariable.id, model_id=model.id).delete()
    db.session.commit()
    Relation.query.filter_by(influenced_id=corevariable.id, model_id=model.id).delete()
    db.session.commit()

    # Als de kernvariabele al een vragenlijstgroep had binnen de vragenlijst deze en de bijbehorende vragen verwijderen.
    if questionnaire:
        questiongroup = QuestionGroup.query.filter_by(corevariable_id=corevariable.id,
                                                      questionnaire_id=questionnaire.id).first()
        Question.query.filter_by(questiongroup_id=questiongroup.id).delete()
        db.session.commit()
        QuestionGroup.query.filter_by(corevariable_id=corevariable.id, questionnaire_id=questionnaire.id).delete()
        db.session.commit()

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
    form.name_influencer.choices = [(corevariable.id, corevariable.name) for corevariable in
                                    model.linked_corevariables]
    form.name_influenced.choices = [(corevariable.id, corevariable.name) for corevariable in
                                    model.linked_corevariables]

    # Als de gebruiker aangeeft een nieuwe relatie aan te willen maken.
    if form.validate_on_submit():
        # De ID van de beïnvloedende kernvariabele bepalen.
        id_influencer = [corevariable for corevariable in model.linked_corevariables if corevariable.id ==
                         int(form.name_influencer.data)][0].id
        # De ID van de beïnvloedde kernvariabele bepalen.
        id_influenced = [corevariable for corevariable in model.linked_corevariables if corevariable.id ==
                         int(form.name_influenced.data)][0].id

        if Relation.query.filter_by(model_id=model.id, influencer_id=id_influencer,
                                    influenced_id=id_influenced).first() is None:
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


#############################################################################################################
#                                        Vragenlijst opstellen
#############################################################################################################


@bp.route('/questionnaire/<study_code>', methods=['GET', 'POST'])
@login_required
def questionnaire(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    setup_questiongroups(study)
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()

    # Voor het geval nieuwe kernvariabelen zijn toegevoegd aan het onderzoeksmodel nieuwe vragenlijstgroepen aanmaken.
    for corevariable in model.linked_corevariables:
        if corevariable.id not in [questiongroup.corevariable_id for questiongroup
                                   in QuestionGroup.query.filter_by(questionnaire_id=questionnaire.id)]:
            questiongroup = QuestionGroup(questionnaire_id=questionnaire.id,
                                          corevariable_id=corevariable.id)
            db.session.add(questiongroup)
            db.session.commit()

    questiongroups = [questiongroup for questiongroup in questionnaire.linked_questiongroups]

    # Een dictionary met sublijsten van alle vragen per vragenlijstgroep/kernvariabele (questiongroups_questions)
    # en de opzet ervan
    questions = []
    for questiongroup in questiongroups:
        questions.append(questiongroup.linked_questions())
    questiongroups_questions = dict(zip(questiongroups, questions))

    # Een lijst met de demographics die bij het onderzoek horen.
    demographics = [demographic for demographic in questionnaire.linked_demographics]

    return render_template("create_study/questionnaire.html", title='Questionnaire', study=study, model=model,
                           questiongroups=questiongroups, questionnaire=questionnaire,
                           questiongroups_questions=questiongroups_questions, demographics=demographics)


@bp.route('/questionnaire/edit_scale/<study_code>', methods=['GET', 'POST'])
@login_required
def edit_scale(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()

    # De Form voor het aanpassen van het onderzoek.
    form = EditScaleForm(questionnaire.scale)

    # Als de gebruiker aangeeft de onderzoek te willen aanpassen met de gegeven gegevens.
    if form.validate_on_submit():
        # De gegevens van de studie worden aangepast naar de ingegeven data binnen de Form.
        questionnaire.scale = form.scale_questionnaire.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('create_study.questionnaire', study_code=study.code))
    # Als niks is ingegeven binnen de Form worden geen aanpassingen gemaakt (en dus gebruikgemaakt van de eigen
    # onderzoeksgegevens.
    elif request.method == 'GET':
        form.scale_questionnaire.data = questionnaire.scale

    return render_template('create_study/edit_scale.html', title='Edit scale', form=form, study=study)


@bp.route('/questionnaire/new_demographic/<study_code>', methods=['GET', 'POST'])
@login_required
def new_demographic(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    demographics = [demographic for demographic in Demographic.query.filter_by(user_id=current_user.id)]
    amount_of_demographics = len(demographics)

    return render_template("create_study/new_demographic.html", title="New Demographic", study=study, model=model,
                           demographics=demographics, amount_of_demographics=amount_of_demographics)


@bp.route('/add_demographic/<study_code>/<demographic_id>', methods=['GET', 'POST'])
@login_required
def add_demographic(study_code, demographic_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    demographic = Demographic.query.filter_by(id=demographic_id).first()

    demographic.link(questionnaire)
    db.session.commit()

    return redirect(url_for('create_study.questionnaire', study_code=study_code))


@bp.route('/questionnaire/create_new_demographic/<study_code>', methods=['GET', 'POST'])
@login_required
def create_new_demographic(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()

    # De Form voor het aanmaken van een nieuwe demografiek.
    form = CreateNewDemographicForm()

    # Als de gebruiker aangeeft een nieuwe demografiek aan te maken met de gegeven gegevens.
    if form.validate_on_submit():
        new_demographic = Demographic(name=form.name_of_demographic.data,
                                      description=form.description_of_demographic.data,
                                      optional=form.optionality_of_demographic.data,
                                      questiontype=form.type_of_demographic.data,
                                      user_id=current_user.id)
        db.session.add(new_demographic)
        new_demographic.link(questionnaire)
        db.session.commit()

        for demographic_option in form.choices_of_demographic.data.split(','):
            new_demographic_option = DemographicOption(name=demographic_option, demographic_id=new_demographic.id)
            db.session.add(new_demographic_option)
            db.session.commit()

        return redirect(url_for("create_study.questionnaire", study_code=study_code))

    return render_template("create_study/create_new_demographic.html", title="New Demographic", form=form)


@bp.route('/remove_demographic/<study_code>/<demographic_id>', methods=['GET', 'POST'])
@login_required
def remove_demographic(study_code, demographic_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    demographic = Demographic.query.filter_by(id=demographic_id).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()

    demographic.unlink(questionnaire)
    db.session.commit()

    return redirect(url_for('create_study.questionnaire', study_code=study_code))


@bp.route('/questionnaire/new_question/<study_code>/<corevariable_id>', methods=['GET', 'POST'])
@login_required
def new_question(study_code, corevariable_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()
    questiongroups = [questiongroup for questiongroup in
                      QuestionGroup.query.filter_by(questionnaire_id=questionnaire.id)]

    return render_template("create_study/new_question.html", title="New question", study=study,
                           corevariable=corevariable, questiongroups=questiongroups, corevariable_id=corevariable_id)


@bp.route('/add_question/<study_code>/<corevariable_id>/<question_id>', methods=['GET', 'POST'])
@login_required
def add_question(study_code, corevariable_id, question_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    question = Question.query.filter_by(id=question_id).first()

    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    questiongroup = QuestionGroup.query.filter_by(questionnaire_id=questionnaire.id,
                                                  corevariable_id=corevariable_id).first()

    # De bijbehorende kernvariabele verkrijgen voor het bepalen van de afkorting van de correcte variabele.
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()
    abbreviation_corevariable = corevariable.abbreviation

    # De code voor de vraag (de kernvariabele plus een cijfer, zoals "PE3")
    new_code = abbreviation_corevariable + str(len([question for question in
                                                    Question.query.filter_by(
                                                        questiongroup_id=questiongroup.id)]) + 1)

    # Het aanmaken van een nieuwe vraag in de database.
    new_question = Question(question=question.question,
                            questiongroup_id=questiongroup.id,
                            question_code=new_code)
    db.session.add(new_question)
    db.session.commit()

    return redirect(url_for('create_study.questionnaire', study_code=study_code))


@bp.route('/questionnaire/create_new_question/<study_code>/<corevariable_id>', methods=['GET', 'POST'])
@login_required
def create_new_question(study_code, corevariable_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()
    # De Form voor het aanmaken van een nieuwe vraag.
    form = CreateNewQuestionForm()

    # Als de gebruiker aangeeft een nieuwe vraag aan te maken met de gegeven gegevens.
    if form.validate_on_submit():
        questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
        questiongroup = QuestionGroup.query.filter_by(questionnaire_id=questionnaire.id,
                                                      corevariable_id=corevariable_id).first()

        # De bijbehorende kernvariabele verkrijgen voor het bepalen van de afkorting van de correcte variabele.
        corevariable = CoreVariable.query.filter_by(id=corevariable_id).first()
        abbreviation_corevariable = corevariable.abbreviation

        # De code voor de vraag (de kernvariabele plus een cijfer, zoals "PE3")
        new_code = abbreviation_corevariable + str(len([question for question in
                                                        Question.query.filter_by(
                                                            questiongroup_id=questiongroup.id)]) + 1)

        # Het aanmaken van een nieuwe vraag in de database.
        new_question = Question(question=form.name_question.data,
                                questiongroup_id=questiongroup.id,
                                question_code=new_code,
                                user_id=current_user.id)
        db.session.add(new_question)
        db.session.commit()

        return redirect(url_for("create_study.questionnaire", study_code=study_code))

    return render_template("create_study/create_new_question.html", title="Create new question", form=form,
                           corevariable=corevariable)


@bp.route('/questionnaire/edit_question/<study_code>/<question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(study_code, question_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    question = Question.query.filter_by(id=question_id).first()

    # De Form voor het aanpassen van het onderzoek.
    form = EditQuestionForm(question.question)

    # Als de gebruiker aangeeft de onderzoek te willen aanpassen met de gegeven gegevens.
    if form.validate_on_submit():
        # De gegevens van de studie worden aangepast naar de ingegeven data binnen de Form.
        question.question = form.name_question.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('create_study.questionnaire', study_code=study.code))
    # Als niks is ingegeven binnen de Form worden geen aanpassingen gemaakt (en dus gebruikgemaakt van de eigen
    # onderzoeksgegevens.
    elif request.method == 'GET':
        form.name_question.data = question.question
    return render_template('create_study/edit_question.html', title='Edit Profile',
                           form=form, study=study)


@bp.route('/remove_question/<study_code>/<question_id>', methods=['GET', 'POST'])
@login_required
def remove_question(study_code, question_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    # Het verwijderen van de vraag uit de database.
    Question.query.filter_by(id=question_id).delete()
    db.session.commit()

    return redirect(url_for('create_study.questionnaire', study_code=study_code))


@bp.route('/questionnaire/switch_reversed_score/<study_code>/<question_id>', methods=['GET', 'POST'])
@login_required
def switch_reversed_score(study_code, question_id):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    # De reversed_score aan- of uitzetten voor de vraag afhankelijk wat de huidige stand is.
    question = Question.query.filter_by(id=question_id).first()
    if question.reversed_score:
        question.reversed_score = False
        db.session.commit()
    else:
        question.reversed_score = True
        db.session.commit()
    return redirect(url_for('create_study.questionnaire', study_code=study_code))


#############################################################################################################
#                                          Start onderzoek
#############################################################################################################

@bp.route('/starting_study/<study_code>', methods=['GET', 'POST'])
@login_required
def starting_study(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    study = Study.query.filter_by(code=study_code).first()
    if current_user not in study.linked_users:
        return redirect(url_for('main.not_authorized'))

    # Checken hoe ver de studie is
    if study.stage_2:
        return redirect(url_for('create_study.study_underway', name_study=study.name, study_code=study_code))
    if study.stage_3:
        return redirect(url_for('create_study.summary_results', study_code=study_code))

    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    questiongroups = [questiongroup for questiongroup in questionnaire.linked_questiongroups]

    # Bepalen of alle vragenlijstgroepen tenminste één vraag hebben en er een schaal is gegeven voor de vragenlijst.
    # Zo niet, de Flash geven en terugkeren.
    for questiongroup in questiongroups:
        if Question.query.filter_by(questiongroup_id=questiongroup.id).count() == 0:
            flash('One or more of the core variables does not have questions yet. Please add at least one question to '
                  'each core variable.')
            return redirect(url_for('create_study.questionnaire', study_code=study.code))

    if questionnaire.scale is None or 4 > questionnaire.scale or questionnaire.scale > 10:
        flash('A correct scale has not been given yet for the questionnaire. Please select a scale between 4 and 10.')
        return redirect(url_for('create_study.questionnaire', study_code=study.code))

    # Omzetting studie van stage_1 (opstellen van het onderzoek) naar stage_2 (het onderzoek is gaande)
    study.stage_1 = False
    study.stage_2 = True
    db.session.commit()

    return redirect(url_for('create_study.study_underway', name_study=study.name, study_code=study_code))


@bp.route('/study_underway/<name_study>/<study_code>', methods=['GET', 'POST'])
@login_required
def study_underway(name_study, study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)
    # De link naar de vragenlijst
    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    link = '127.0.0.1:5000/d/e/{}'.format(study.code)

    return render_template('create_study/study_underway.html', title="Underway: {}".format(name_study), study=study,
                           link=link, questionnaire=questionnaire)


@bp.route('/end_study/<study_code>', methods=['GET', 'POST'])
@login_required
def end_study(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    # Omzetting studie van stage_2 (het onderzoek is gaande) naar stage_3 (de data-analyse)
    study.stage_2 = False
    study.stage_3 = True
    db.session.commit()

    return redirect(url_for('create_study.summary_results', study_code=study_code))


#############################################################################################################
#                                     Data Analyse en visualisatie
#############################################################################################################

@bp.route('/summary_results/<study_code>', methods=['GET', 'POST'])
@login_required
def summary_results(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    demographics = [demographic for demographic in questionnaire.linked_demographics]
    questions = [question for question in questionnaire.linked_questions()]
    cases = [case for case in questionnaire.linked_cases()]

    return render_template('create_study/summary_results.html', study_code=study_code, demographics=demographics,
                           questions=questions, cases=cases, study=study)


@bp.route('/data_analysis/<study_code>', methods=['GET', 'POST'])
@login_required
def data_analysis(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    security_and_studycheck(study_code)

    study = Study.query.filter_by(code=study_code).first()
    questionnaire = Questionnaire.query.filter_by(study_id=study.id).first()
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    corevariables = [corevariable for corevariable in model.linked_corevariables]

    # Het opzetten van de dataframe (gebruik van plspm package en pd.dataframe met de vragenlijstresultaten)
    questiongroups = [questiongroup for questiongroup in questionnaire.linked_questiongroups]
    questionlist_and_answerlist = return_questionlist_and_answerlist(questiongroups)
    list_of_questions = questionlist_and_answerlist[0]
    list_of_answers = questionlist_and_answerlist[1]

    df = pd.DataFrame(list_of_answers).transpose()
    df.columns = list_of_questions

    structure = setup_structure_dataframe(corevariables, model.id)

    config = c.Config(structure.path(), scaled=False)
    scheme = Scheme.CENTROID

    for corevariable in corevariables:
        config.add_lv_with_columns_named(corevariable.abbreviation, Mode.A, df, corevariable.abbreviation)

    plspm_calc = Plspm(df, config, scheme)
    plspm_model = plspm_calc.outer_model()

    # Creëert dictionary met alleen loadings van latente variabele
    loadings_dct = pd.DataFrame(plspm_model['loading']).to_dict('dict')['loading']

    # Een matrix van Heterotrait-Monotrait Ratio wordt hier beschikbaar gemaakt (module "htmt_matrix" staat bovenaan
    # verwezen.
    data_htmt = htmt_matrix(df, model)
    amount_of_variables = len(corevariables)

    # Buitenste VIF-waarden worden hier beschikbaar gemaakt in een dictionary onder "data_outer_vif". Module bovenaan
    # geïmporteerd.
    data_outer_vif = outer_vif_values_dict(df, questionnaire)

    model.edited = False
    db.session.commit()

    return render_template('create_study/data_analysis.html', study_code=study_code, df=df, config=config, scheme=scheme,
                           data_outer_vif=data_outer_vif, questiongroups=questiongroups, model=model,
                           data_htmt=data_htmt, amount_of_variables=amount_of_variables, study=study,
                           loadings_dct=loadings_dct)