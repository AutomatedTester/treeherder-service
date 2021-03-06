import pytest
import simplejson as json

from ..sampledata import SampleData
from treeherder.log_parser.utils import get_mozharness_substring


@pytest.fixture
def jobs_with_local_log(initial_data):
    log = "mozilla-inbound_ubuntu64_vm-debug_test-mochitest-other-bm53-tests1-linux-build122"
    sample_data = SampleData()
    url = "file://{0}".format(
        sample_data.get_log_path("{0}.txt.gz".format(log)))

    job = sample_data.job_data[0]

    # substitute the log url with a local url
    job['job']['log_references'][0]['url'] = url
    return [job]


def test_parse_log(jm, initial_data, jobs_with_local_log, sample_resultset, mock_send_request):
    """
    check that at least 2 job_artifacts get inserted when running
    a parse_log task
    """

    jm.store_result_set_data(sample_resultset)

    jobs = jobs_with_local_log
    for job in jobs:
        # make this a successful job, so no error log processing
        job['job']['result'] = "success"
        job['revision_hash'] = sample_resultset[0]['revision_hash']

    jm.store_job_data(jobs)
    jm.process_objects(1, raise_errors=True)

    job_id = jm.get_jobs_dhub().execute(
        proc="jobs_test.selects.row_by_guid",
        placeholders=[jobs[0]['job']['job_guid']]
    )[0]['id']

    job_artifacts = jm.get_jobs_dhub().execute(
        proc="jobs_test.selects.job_artifact",
        placeholders=[job_id]
    )

    jm.disconnect()

    # we must have at least 2 artifacts: one for the log viewer and another one
    # for the job artifact panel

    assert len(job_artifacts) >= 2


def test_bug_suggestions_artifact(jm, initial_data, jobs_with_local_log,
                                  sample_resultset, mock_send_request,
                                  mock_get_remote_content
                                  ):
    """
    check that at least 2 job_artifacts get inserted when running
    a parse_log task
    """
    jm.store_result_set_data(sample_resultset)

    jobs = jobs_with_local_log
    for job in jobs:
        # make this a failing job, so use error log processing
        job['job']['result'] = "testfailed"
        job['revision_hash'] = sample_resultset[0]['revision_hash']

    jm.store_job_data(jobs)
    jm.process_objects(1, raise_errors=True)

    job_id = jm.get_jobs_dhub().execute(
        proc="jobs_test.selects.row_by_guid",
        placeholders=[jobs[0]['job']['job_guid']]
    )[0]['id']

    job_artifacts = jm.get_jobs_dhub().execute(
        proc="jobs_test.selects.job_artifact",
        placeholders=[job_id]
    )

    jm.disconnect()

    # we must have at least 3 artifacts:
    # 1 for the log viewer
    # 1 for the job artifact panel
    # 1 for the bug suggestions
    assert len(job_artifacts) >= 3

    structured_log_artifact = [artifact for artifact in job_artifacts
                               if artifact["name"] == "Structured Log"][0]
    bug_suggestions_artifact = [artifact for artifact in job_artifacts
                                if artifact["name"] == "Bug suggestions"][0]
    structured_log = json.loads(structured_log_artifact["blob"])

    all_errors = structured_log["step_data"]["all_errors"]
    bug_suggestions = json.loads(bug_suggestions_artifact["blob"])

    # we must have one bugs item per error in bug_suggestions.
    # errors with no bug suggestions will just have an empty
    # bugs list
    assert len(all_errors) == len(bug_suggestions)
