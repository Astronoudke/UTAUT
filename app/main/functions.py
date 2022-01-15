from flask import render_template, flash, redirect, url_for, request
from app.models import Study, CoreVariable, Relation, ResearchModel
from flask_login import current_user


def security_and_studycheck(study_code):
    # Checken of gebruiker tot betrokken onderzoekers hoort
    study = Study.query.filter_by(code=study_code).first()
    if current_user not in study.linked_users:
        print("Not authorized")
        return redirect(url_for('main.not_authorized'))

    # Checken hoe ver de studie is
    if study.stage_2:
        return redirect(url_for('new_study.study_underway', name_study=study.name, study_code=study_code))
    if study.stage_3:
        return redirect(url_for('new_study.summary_results', study_code=study_code))
