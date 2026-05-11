# Commit Format

See `.project/ENGINEERING-MANUAL.md` §3.3 for the full table. Quick reference:

```
<emoji> <type>(<scope>): <description>
```

**Examples:**

✅ `✨ feat(scraper): MVP Playwright scraper for keyword search`
✅ `🐛 fix(parser): handle missing page_name in commercial ad cards`
✅ `🧪 test(retry): cover rate-limit retry timing`
✅ `📝 docs(approach): one-pager approach explanation`
✅ `♻️ refactor(scraper): extract pagination into pagination.py`

❌ `feat: add stuff and fix bug` (multiple changes, no scope, no emoji)
❌ `WIP` (uninformative)
❌ `Update README.md` (no scope, no type)
