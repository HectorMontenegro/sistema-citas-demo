from pathlib import Path


def test_runtime_sources_do_not_contain_the_removed_target_or_live_selectors():
    root = Path(__file__).parents[1]
    source_paths = [root / "src", root / "google_apps_script", root / "sql"]
    content = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for source_path in source_paths
        for path in source_path.rglob("*")
        if path.is_file()
    )

    forbidden_markers = [
        "us" + "visa-info",
        "appointments_" + "submit",
        "user_" + "password",
        "smtp." + "gmail.com",
        "webdriver_" + "manager",
    ]
    assert all(marker not in content for marker in forbidden_markers)
