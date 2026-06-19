# urirun PHP site

Serve the documentation site from the repository root:

```bash
php -S 127.0.0.1:8098 -t www
```

The site reads Markdown documents from `../docs/` and uses copied SVG logo
assets from `www/assets/`.

Routes:

- `/index.php` - project overview, quickstart, workflow, examples, and roadmap.
- `/docs.php?doc=getting-started` - Markdown docs rendered from `../docs/`.
- `/index.html` - static redirect to the PHP entry point.
