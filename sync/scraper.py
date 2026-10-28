import re


def scrape_code_and_percentiles(page, submission_id):
    page.goto(f"https://leetcode.com/submissions/detail/{submission_id}/", wait_until="domcontentloaded")
    # Wait for percentiles (hydrated DOM)
    page.wait_for_selector(
        'span[class*="text-lg"][class*="font-semibold"][class*="text-sd-foreground"]',
        timeout=60000
    )

    page.wait_for_function("""() => {
        const values = Array.from(document.querySelectorAll(
            'span[class*="text-lg"][class*="font-semibold"][class*="text-sd-foreground"]'
        ));
        return values.length >= 4 && values.slice(0, 4).every(el => el.innerText.trim());
    }""", timeout=60000)

    # Extract percentiles
    spans = page.evaluate("""
    () => Array.from(
        document.querySelectorAll('span[class*="text-lg"][class*="font-semibold"][class*="text-sd-foreground"]')
    ).map(el => el.innerText.trim());
    """)
    runtime = spans[0] if len(spans) > 0 else None
    runtime_pct = spans[1] if len(spans) > 1 else None
    memory = spans[2] if len(spans) > 2 else None
    memory_pct = spans[3] if len(spans) > 3 else None

    # Extract code from Prism <code> block
    page.wait_for_selector("code[class^='language-']", timeout=60000)
    code_raw = page.locator("code[class^='language-']").inner_text()
    code = normalize_code(code_raw)
    if not all((runtime, runtime_pct, memory, memory_pct, code)):
        raise RuntimeError("Submission page is missing code or performance details")
    for value in (runtime_pct, memory_pct):
        if not re.fullmatch(r"\d+(?:\.\d+)?%?", value.strip()) or not 0 <= float(value.rstrip("%")) <= 100:
            raise RuntimeError("Submission percentiles could not be read")

    return {
        "id": submission_id,
        "code": code,
        "runtime": with_unit(runtime, "ms"),
        "runtime_percentile": runtime_pct,
        "memory": with_unit(memory, "MB"),
        "memory_percentile": memory_pct
    }
def with_unit(value, unit):
    value = value.strip()
    return value if value.lower().endswith(unit.lower()) else value + unit


def normalize_code(raw):
    # Prism text is already decoded source. Preserve literal escapes and digits.
    return raw.strip() if raw is not None else None
