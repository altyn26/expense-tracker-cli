"""Tests for the optional matplotlib dependency (finding F8).
Chart files are written to a temporary directory, never to charts/."""
import subprocess
import sys
from pathlib import Path

import pytest

from visualization import ChartGenerator

REPO_ROOT = Path(__file__).resolve().parent.parent


# AC7a: the CLI module must import even when matplotlib is unavailable
def test_main_imports_without_matplotlib():
    code = (
        "import sys; sys.modules['matplotlib'] = None; "
        "import main; print('import ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "import ok" in result.stdout


@pytest.fixture
def charts(tmp_path):
    pytest.importorskip("matplotlib")
    return ChartGenerator(charts_dir=tmp_path)


# AC7b: charts are still produced when matplotlib is present
def test_bar_chart_creates_png(charts):
    path = Path(charts.bar_chart({"Food": 10.0, "Rent": 20.0}))
    assert path.is_file()
    assert path.suffix == ".png"


def test_pie_chart_creates_png(charts):
    path = Path(charts.pie_chart({"Food": 10.0, "Rent": 20.0}))
    assert path.is_file()
    assert path.suffix == ".png"