import pytest
import os
import json

from treeherder.etl.bugzilla import BzApiBugProcess


@pytest.fixture
def mock_extract(monkeypatch):
    """
    mock BzApiBugProcess._get_bz_source_url() to return
    a local sample file
    """
    def extract(obj, url):
        tests_folder = os.path.dirname(os.path.dirname(__file__))
        bug_list_path = os.path.join(
            tests_folder,
            "sample_data",
            "bug_list.json"
        )
        content = json.loads(open(bug_list_path).read())
        return content


    monkeypatch.setattr(BzApiBugProcess,
                        'extract',
                        extract)


def test_bz_api_process(mock_extract, refdata):
    process = BzApiBugProcess()
    process.run()

    row_data = refdata.dhub.execute(
        proc='refdata_test.selects.test_bugscache',
        return_type='tuple'
    )

    refdata.disconnect()

    # the number of rows inserted should equal to the number of bugs
    assert len(row_data) == 10

    # test that a second ingestion of the same bugs doesn't insert new rows
    process.run()
    assert len(row_data) == 10
