"""Avancement des synthèses d'un sondage et temps restant estimé (EPF-MDE/OceENS#149).

Le nombre vient du Design Document v1 (EPF-MDE/OceENS#121) : 45 jobs par
sondage (A), 20 s par job (B), et un sondage prêt en 1 h 30 au plus, même si
chaque job atteint le plafond de 120 s (D).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.summary_progress import progress

PENDING, DONE, TIMEOUT = 0, 200, 504


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def queue(session, survey_id, count, http_status=PENDING, summary_text=None):
    session.add_all(
        Summary(survey_id=survey_id, http_status=http_status, summary_text=summary_text)
        for _ in range(count)
    )
    session.commit()


def test_a_survey_just_clicked_is_estimated_at_about_15_minutes(session):
    queue(session, survey_id=1, count=45)

    result = progress(session, 1)

    assert result.total == 45
    assert result.done == 0
    assert result.errors == 0
    assert result.finished is False
    assert result.estimated_seconds_left == 900


def test_at_the_120_s_cap_a_survey_is_still_ready_within_1_h_30(session):
    queue(session, survey_id=1, count=45)

    result = progress(session, 1, seconds_per_job=120)

    assert result.estimated_seconds_left == 5400
    assert result.estimated_seconds_left <= 90 * 60


def test_the_estimate_counts_the_jobs_of_every_survey_in_the_queue(session):
    queue(session, survey_id=1, count=45)
    queue(session, survey_id=2, count=45)

    assert progress(session, 1).estimated_seconds_left == 1800


def test_a_survey_with_no_pending_job_is_finished_with_nothing_left(session):
    queue(session, survey_id=1, count=39, http_status=DONE, summary_text="<p>ok</p>")
    queue(session, survey_id=1, count=1, http_status=DONE, summary_text=None)
    queue(session, survey_id=1, count=5, http_status=TIMEOUT)

    result = progress(session, 1)

    assert result.total == 45
    assert result.done == 40
    assert result.errors == 5
    assert result.finished is True
    assert result.estimated_seconds_left == 0


def test_a_survey_with_no_job_is_not_finished(session):
    queue(session, survey_id=2, count=3)

    result = progress(session, 1)

    assert result.total == 0
    assert result.finished is False
    assert result.estimated_seconds_left == 0


def test_a_job_duration_of_zero_is_refused(session):
    queue(session, survey_id=1, count=45)

    with pytest.raises(ValueError):
        progress(session, 1, seconds_per_job=0)
