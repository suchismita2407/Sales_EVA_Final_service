from types import SimpleNamespace


def test_generate_gap_pdf_writes_report(tmp_path, monkeypatch):
    from services import report_service

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        report_service,
        "query_one",
        lambda query, _params: (
            {"name": "Opportunity", "description": "Need analytics"}
            if "opportunities" in query
            else {"name": "Offering", "description": "Analytics platform"}
        ),
    )
    monkeypatch.setattr(report_service, "analyze_gaps", lambda *_args: {
        "covered": ["Reporting"],
        "partial": [],
        "missing": ["Migration"],
    })
    monkeypatch.setattr(
        report_service,
        "get_llm",
        lambda: SimpleNamespace(invoke=lambda _prompt: SimpleNamespace(content="- Recommend a pilot")),
    )

    output_path = report_service.generate_gap_pdf(1, 2)

    report = tmp_path / output_path
    assert report.exists()
    assert report.read_bytes().startswith(b"%PDF")