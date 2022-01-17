from app.models import ResearchModel, Questionnaire, QuestionGroup
from app import db


def setup_questiongroups(study):
    model = ResearchModel.query.filter_by(id=study.researchmodel_id).first()
    if Questionnaire.query.filter_by(study_id=study.id).first() is None:
        new_questionnaire = Questionnaire(study_id=study.id)
        db.session.add(new_questionnaire)
        db.session.commit()

        # Vragenlijstgroepen aanmaken per kernvariabele.
        for corevariable in model.linked_corevariables:
            questiongroup = QuestionGroup(questionnaire_id=new_questionnaire.id, corevariable_id=corevariable.id)
            db.session.add(questiongroup)
            db.session.commit()
