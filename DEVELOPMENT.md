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
