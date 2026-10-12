from scripts.verify_ci_before_deploy import REQUIRED_WORKFLOWS, verdict

SHA = "a" * 40


def run(path, *, run_id=1, sha=SHA, status="completed", conclusion="success"):
    return dict(path=path, id=run_id, head_sha=sha, head_branch="main",
                event="push", status=status, conclusion=conclusion)


def test_requires_both_workflows_for_exact_commit():
    runs = [run(path) for path in REQUIRED_WORKFLOWS]
    assert verdict(runs, SHA)[0] == "success"
    assert verdict(runs[:1], SHA)[0] == "pending"
    assert verdict(runs, "b" * 40)[0] == "pending"


def test_newer_failure_cannot_be_hidden_by_old_success():
    runs = [run(path) for path in REQUIRED_WORKFLOWS]
    runs.append(run(REQUIRED_WORKFLOWS[0], run_id=2, conclusion="failure"))
    assert verdict(runs, SHA)[0] == "failed"


def test_running_or_skipped_checks_do_not_allow_deployment():
    for status, conclusion, expected in [
        ("in_progress", None, "pending"),
        ("completed", "skipped", "failed"),
        ("completed", "cancelled", "failed"),
    ]:
        runs = [run(path) for path in REQUIRED_WORKFLOWS]
        runs[0] = run(REQUIRED_WORKFLOWS[0], status=status, conclusion=conclusion)
        assert verdict(runs, SHA)[0] == expected


def test_pull_request_check_is_not_production_commit_evidence():
    runs = [run(path) for path in REQUIRED_WORKFLOWS]
    runs[0]["event"] = "pull_request"
    assert verdict(runs, SHA)[0] == "pending"
