from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8514"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def wait(page, ms=3500):
    page.wait_for_timeout(ms)


def shot(page, name, ms=2500):
    wait(page, ms)
    page.screenshot(path=str(OUT / name), full_page=True)
    print(f"saved {name}")


def scroll_shot(page, name, y=850, ms=1500):
    page.evaluate("window.scrollTo(0, 0)")
    wait(page, 500)
    page.mouse.wheel(0, y)
    shot(page, name, ms=ms)
    page.evaluate("window.scrollTo(0, 0)")


def top(page):
    page.evaluate("window.scrollTo(0, 0)")
    wait(page, 800)


def click_button(page, name):
    selectors = [
        lambda: page.get_by_role("button", name=name, exact=True),
        lambda: page.get_by_text(name, exact=True).first,
    ]
    for selector in selectors:
        try:
            selector().click(timeout=9000)
            return True
        except Exception:
            continue
    print(f"click failed: {name}")
    return False


def click_text(page, name):
    try:
        page.get_by_text(name, exact=True).first.click(timeout=7000)
        return True
    except Exception:
        print(f"text/tab failed: {name}")
        return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROME)
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    wait(page, 9000)
    shot(page, "01_home.png")

    if click_button(page, "Benchmark & Examples"):
        wait(page, 5000)
        top(page)
        shot(page, "02_benchmark_article_reproducibility.png")
        scroll_shot(page, "02_benchmark_article_reproducibility_scroll.png", y=1000)
        for tab, name in [
            ("Run Benchmark", "03_benchmark_run.png"),
            ("Concepts", "04_benchmark_concepts.png"),
            ("Article Reproducibility", "05_benchmark_article_reproducibility_again.png"),
        ]:
            if click_text(page, tab):
                top(page)
                shot(page, name)
                if tab in {"Run Benchmark", "Concepts"}:
                    scroll_shot(page, name.replace(".png", "_scroll.png"), y=1000)

    if click_button(page, "Scenario Studio"):
        wait(page, 5000)
        top(page)
        shot(page, "06_scenario_studio_overview.png")
        scroll_shot(page, "07_scenario_studio_source_scroll.png", y=950)
        scroll_shot(page, "08_scenario_studio_validation_scroll.png", y=1900)
        scroll_shot(page, "10_scenario_model_training.png", y=3000)

    if click_button(page, "Study Lab"):
        wait(page, 5000)
        top(page)
        shot(page, "11_study_deep_learning_workbench.png")
        for tab, name in [
            ("Original VMamba", "12_study_original_vmamba.png"),
            ("Official Runtime", "13_study_official_runtime.png"),
            ("Run SS2D Demo", "14_study_ss2d_demo.png"),
            ("VMamba-Mesh Changes", "15_study_mesh_changes.png"),
            ("Train Model Adapter", "16_study_train_model_adapter.png"),
            ("Model Reports", "17_study_model_reports.png"),
            ("Model Interpretability", "18_study_model_interpretability.png"),
            ("Knowledge Base", "19_study_knowledge_base.png"),
        ]:
            if click_text(page, tab):
                top(page)
                shot(page, name)
                if tab in {"Train Model Adapter", "Model Reports", "Model Interpretability", "Knowledge Base"}:
                    scroll_shot(page, name.replace(".png", "_scroll.png"), y=1000)

    if click_button(page, "Model Lab"):
        wait(page, 5000)
        top(page)
        shot(page, "20_model_lab.png")
        scroll_shot(page, "20_model_lab_scroll.png", y=1000)

    if click_button(page, "Research Reports"):
        wait(page, 5000)
        top(page)
        shot(page, "21_research_reports.png")
        scroll_shot(page, "21_research_reports_scroll.png", y=1000)

    if click_button(page, "Admin"):
        wait(page, 5000)
        top(page)
        shot(page, "22_admin_overview.png")
        for tab, name in [
            ("Backend Store", "23_admin_backend_store.png"),
            ("Scenario Warehouse", "24_admin_scenario_warehouse.png"),
            ("Neo4j", "25_admin_neo4j.png"),
            ("Settings", "26_admin_settings.png"),
        ]:
            if click_text(page, tab):
                top(page)
                shot(page, name)
                scroll_shot(page, name.replace(".png", "_scroll.png"), y=1000)

    if click_button(page, "Logs"):
        wait(page, 4000)
        top(page)
        shot(page, "27_logs_session.png")
        if click_text(page, "Terminal Logs"):
            top(page)
            shot(page, "28_logs_terminal.png")

    if click_button(page, "Help"):
        wait(page, 5000)
        top(page)
        shot(page, "29_help_presentation.png")
        scroll_shot(page, "29_help_presentation_scroll.png", y=1000)
        if click_text(page, "Tech Docs"):
            top(page)
            shot(page, "30_help_tech_docs.png")
            scroll_shot(page, "30_help_tech_docs_scroll.png", y=1000)

    if click_button(page, "About"):
        wait(page, 5000)
        top(page)
        shot(page, "31_about.png")
        scroll_shot(page, "31_about_scroll.png", y=1000)

    browser.close()
