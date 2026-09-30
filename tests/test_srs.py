import random
from datetime import date, timedelta

from bivouac.domain.model import Card, CardKind
from bivouac.domain.srs import Grade, choice_question, review

TODAY = date(2026, 10, 1)


def test_good_answers_space_out():
    s = review(None, "c", Grade.GOOD, TODAY)
    assert (s.interval, s.due) == (1, TODAY + timedelta(days=1))
    s = review(s, "c", Grade.GOOD, s.due)
    assert s.interval == 3
    s = review(s, "c", Grade.GOOD, s.due)
    assert s.interval == round(3 * 2.5) and s.reps == 3


def test_again_resets_and_lowers_ease():
    s = review(review(None, "c", Grade.GOOD, TODAY), "c", Grade.GOOD, TODAY)
    s = review(s, "c", Grade.AGAIN, TODAY)
    assert s.interval == 0 and s.reps == 0 and s.lapses == 1 and s.due == TODAY
    assert s.ease == 2.3


def test_easy_jumps_further_than_good():
    assert review(None, "c", Grade.EASY, TODAY).interval > review(None, "c", Grade.GOOD, TODAY).interval


def test_competition_day_caps_the_gap():
    s = review(None, "c", Grade.EASY, TODAY)
    for _ in range(5):
        s = review(s, "c", Grade.EASY, TODAY, deadline=TODAY + timedelta(days=10))
    assert s.interval <= 5  # comes back at least once more before the day


def test_choice_question_has_the_answer_once_and_prefers_the_same_chapter():
    cards = [Card(f"k{i}", CardKind.CONCEPT, f"T{i}", f"meaning {i}", "", "1" if i < 4 else "2")
             for i in range(8)]
    q = choice_question(cards[0], cards, random.Random(1))
    assert q.options[q.answer] == "T0"
    assert len(q.options) == 4 and len(set(q.options)) == 4
    assert set(q.options) == {"T0", "T1", "T2", "T3"}
