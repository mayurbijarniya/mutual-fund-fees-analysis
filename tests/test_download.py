"""The download step's guard rails. No network access."""

import pytest

from funds import download


def test_quarters_cover_the_whole_range():
    quarters = download.quarters(2016, 2017)
    assert quarters[0] == "2016q1"
    assert quarters[-1] == "2017q4"
    assert len(quarters) == 8


def test_a_contact_email_is_required():
    with pytest.raises(ValueError, match="contact email"):
        download.run("just a name")


def test_every_list_year_has_a_published_path():
    assert sorted(download.SERIES_CLASS_FILES) == list(range(2017, 2027))
    for folder, name in download.SERIES_CLASS_FILES.values():
        assert folder in (download.OLD_FOLDER, download.NEW_FOLDER)
        assert name.endswith(".csv")
