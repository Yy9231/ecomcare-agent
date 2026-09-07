from unittest.mock import Mock

import pytest

from app import evaluation


def test_evaluation_reports_actionable_message_when_database_is_offline(monkeypatch) -> None:
    monkeypatch.setattr(evaluation, "evaluate", Mock(side_effect=OSError("connection refused")))

    with pytest.raises(SystemExit, match="docker compose up -d db backend"):
        evaluation.main()
