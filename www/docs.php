<?php
$site = require __DIR__ . '/site-data.php';
$docs = ['index' => ['title' => 'Docs index', 'description' => 'Overview of urirun documentation.']] + $site['docs'];
$docFiles = [
    'index' => 'index.md',
    'getting-started' => 'getting-started.md',
    'naming' => 'naming.md',
    'commands' => 'commands.md',
    'registry-and-bindings' => 'registry-and-bindings.md',
    'transports' => 'transports.md',
    'logo' => 'logo.md',
    'roadmap' => 'roadmap.md',
];

$doc = $_GET['doc'] ?? 'index';
if (!array_key_exists($doc, $docFiles)) {
    http_response_code(404);
    $doc = 'index';
}

$path = __DIR__ . '/../docs/' . $docFiles[$doc];
$markdown = is_file($path) ? file_get_contents($path) : '# Missing document';

function render_markdown(string $markdown): string
{
    $html = '';
    $inCode = false;
    $paragraph = [];
    $inList = false;
    $listItem = null;

    $flushParagraph = static function () use (&$html, &$paragraph): void {
        if ($paragraph === []) {
            return;
        }
        $html .= "<p>" . inline_markdown(implode(' ', $paragraph)) . "</p>\n";
        $paragraph = [];
    };

    $flushListItem = static function () use (&$html, &$listItem): void {
        if ($listItem === null) {
            return;
        }
        $html .= "<li>" . inline_markdown($listItem) . "</li>\n";
        $listItem = null;
    };

    $closeList = static function () use (&$html, &$inList, $flushListItem): void {
        if (!$inList) {
            return;
        }
        $flushListItem();
        $html .= "</ul>\n";
        $inList = false;
    };

    foreach (preg_split('/\R/', $markdown) as $line) {
        if (str_starts_with($line, '```')) {
            $flushParagraph();
            $closeList();
            $html .= $inCode ? "</code></pre>\n" : "<pre><code>";
            $inCode = !$inCode;
            continue;
        }
        if ($inCode) {
            $html .= htmlspecialchars($line, ENT_QUOTES) . "\n";
            continue;
        }
        if ($line === '') {
            $flushParagraph();
            $closeList();
            continue;
        }
        if (preg_match('/^(#{1,3})\s+(.*)$/', $line, $m)) {
            $flushParagraph();
            $closeList();
            $level = strlen($m[1]);
            $text = htmlspecialchars($m[2], ENT_QUOTES);
            $html .= "<h{$level}>{$text}</h{$level}>\n";
            continue;
        }
        if (preg_match('/^-\s+(.*)$/', $line, $m)) {
            $flushParagraph();
            if (!$inList) {
                $html .= "<ul>\n";
                $inList = true;
            }
            $flushListItem();
            $listItem = $m[1];
            continue;
        }
        if ($inList && preg_match('/^\s{2,}(.+)$/', $line, $m)) {
            $listItem = trim(($listItem ?? '') . ' ' . trim($m[1]));
            continue;
        }
        $closeList();
        $paragraph[] = trim($line);
    }
    if ($inCode) {
        $html .= "</code></pre>\n";
    }
    $flushParagraph();
    $closeList();
    return $html;
}

function inline_markdown(string $text): string
{
    $text = htmlspecialchars($text, ENT_QUOTES);
    $text = preg_replace_callback('/\[([^\]]+)\]\(([a-z0-9-]+)\.md\)/i', static function (array $m): string {
        $label = $m[1];
        $slug = $m[2];
        return '<a href="docs.php?doc=' . rawurlencode($slug) . '">' . $label . '</a>';
    }, $text);
    $text = preg_replace('/`([^`]+)`/', '<code>$1</code>', $text);
    $text = preg_replace('/\*\*([^*]+)\*\*/', '<strong>$1</strong>', $text);
    return $text;
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>urirun docs: <?= htmlspecialchars($doc) ?></title>
  <link rel="icon" href="assets/urirun-favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="index.php" aria-label="urirun home">
      <img src="assets/urirun-horizontal.svg" alt="urirun">
    </a>
    <nav>
      <a href="index.php">Home</a>
      <a href="docs.php?doc=commands">Commands</a>
      <a href="https://github.com/tellmesh/urihandler">GitHub</a>
    </nav>
  </header>
  <main class="docs-layout">
    <aside>
      <?php foreach ($docs as $slug => $file): ?>
        <a class="<?= $slug === $doc ? 'active' : '' ?>" href="docs.php?doc=<?= htmlspecialchars($slug, ENT_QUOTES) ?>">
          <span><?= htmlspecialchars($file['title'], ENT_QUOTES) ?></span>
          <small><?= htmlspecialchars($file['description'], ENT_QUOTES) ?></small>
        </a>
      <?php endforeach; ?>
    </aside>
    <article class="doc-body">
      <?= render_markdown($markdown) ?>
    </article>
  </main>
</body>
</html>
