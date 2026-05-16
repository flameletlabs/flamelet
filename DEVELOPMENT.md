# Flamelet Development Guidelines

## ⚠️ MANDATORY: CI Verification After Every Push

**After every `git push`, verify the CI pipeline passes:**

```bash
# Check CI status
gh run list --limit 1 --json status,conclusion

# Expected output: Status: completed | Conclusion: success
```

**If CI fails:**
1. Review the failing job: `gh run view --json jobs -q '.jobs[] | select(.conclusion=="failure")'`
2. Fix the issue (lint, tests, etc.)
3. Commit and push the fix
4. Verify CI passes again

**This prevents broken code from reaching main.** AI must always verify CI before reporting work complete.

---

## Development Workflow

1. **Make changes** to code
2. **Run tests locally** (optional but recommended): `python3 -m pytest tests/ -q`
3. **Run linting locally** (optional but recommended): `ruff check . && ruff format .`
4. **Commit changes** with clear message
5. **Push to remote**: `git push`
6. **Verify CI passes** ← **MANDATORY FOR AI**
7. Only mark task complete when CI ✓

---

## Common CI Failures & Fixes

### Lint Failures ("Check code style" or "Check formatting")
```bash
ruff format .          # Auto-fix formatting
git add -A && git commit -m "style: Apply ruff formatting"
git push
```

### Test Failures
```bash
python3 -m pytest tests/ -q   # Run tests
python3 -m pytest tests/ -vv  # Verbose output
# Fix the failing test, commit, push
```

---

## Why This Is Mandatory

CI catches issues local development misses:
- Code style inconsistencies (ruff)
- Test failures across Python versions (3.10, 3.11, 3.12, 3.13)
- Provisioning failures in dry-run mode (smoke test)
- Hidden import/syntax errors

**Broken code on main affects all developers.** Verify CI always.

---

## Visual Debugging with Playwright

Use Playwright to screenshot and interact with the web UI programmatically — useful for verifying responsive layouts, catching rendering bugs, and testing user flows without a browser.

### Installation

```bash
pip install playwright
python3 -m playwright install chromium
```

### Taking a mobile screenshot

```python
import asyncio
from playwright.async_api import async_playwright

async def screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page = await ctx.new_page()
        await page.goto("http://localhost:7070", wait_until="networkidle")
        await page.wait_for_timeout(800)
        # Navigate to a specific tab
        await page.locator(".tab-nav button", has_text="Operations").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="/tmp/debug.png")
        await browser.close()

asyncio.run(screenshot())
```

### Checking CSS properties at runtime

```python
# Inside a Playwright async context, after page.goto():
display = await page.evaluate("getComputedStyle(document.querySelector('.cards-scroll')).display")
print(display)  # e.g. "flex" or "none"
```

### Asserting visible elements

```python
# Wait for an element to appear
await page.wait_for_selector(".host-card", state="visible", timeout=5000)
count = await page.locator(".host-card").count()
print(f"host cards visible: {count}")

# Read text content
title = await page.locator(".tenant-title").text_content()
```

### Tips

- Always use `wait_until="networkidle"` on `goto()` to let the app fully load.
- Add `wait_for_timeout(800)` after tab/select interactions to let Svelte re-render.
- Pass `viewport` as a dict — width/height are required nested keys, not top-level kwargs.
- `device_scale_factor=2` gives crisp screenshots on retina but keeps CSS pixels at the viewport size.
- Screenshots are saved to absolute paths; use `/tmp/` for quick inspection.
