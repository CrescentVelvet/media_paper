# Update HTML notes: insert arXiv figure images into existing notes
# Uses online arXiv image URLs (no local download needed)

$figDir = "C:\code\media_paper\figures"
$notesDir = "C:\code\media_paper"

# Read combined JSON
$allPapers = Get-Content "$figDir\all_papers_figures.json" -Raw | ConvertFrom-Json

foreach ($paper in $allPapers) {
    $noteFile = Join-Path $notesDir "$($paper.noteFile)"
    
    if (-not (Test-Path $noteFile)) {
        Write-Output "Note not found: $($paper.noteFile)"
        continue
    }
    
    $noteContent = Get-Content $noteFile -Raw -Encoding UTF8
    
    # Build the figures HTML block
    $figHtml = "`n<!-- arXiv HTML 图表 (from https://arxiv.org/html/$($paper.arxivId)) -->`n"
    $figHtml += '<div class="section" style="border-top: 2px solid #333; margin-top: 30px; padding-top: 20px;">' + "`n"
    $figHtml += "<h2 class=\"section-title\">📐 arXiv 论文图表</h2>`n"
    $figHtml += "<p style=\"color: #888; font-size: 0.9em;\">以下图表来自 arXiv HTML 版本，直接引用 arXiv 在线图片</p>`n"
    
    foreach ($fig in $paper.figures) {
        $figHtml += '<div class="figure-block" style="margin: 20px 0; text-align: center;">' + "`n"
        $figHtml += "  <img src=`"$($fig.url)`" alt=`"$($fig.caption)`" style=`"max-width: 100%; border-radius: 8px; border: 1px solid #333;`" loading=`"lazy`" />`n"
        $figHtml += "  <div class=`"caption`" style=`"color: #aaa; font-size: 0.85em; margin-top: 8px; text-align: left; padding: 0 10px;`">$($fig.caption)</div>`n"
        $figHtml += "</div>`n"
    }
    
    $figHtml += "</div>`n"
    
    # Insert before </body> or </html>
    if ($noteContent -match '</body>') {
        $noteContent = $noteContent -replace '</body>', "$figHtml</body>"
    } elseif ($noteContent -match '</html>') {
        $noteContent = $noteContent -replace '</html>', "$figHtml</html>"
    } else {
        # Append at end
        $noteContent += $figHtml
    }
    
    # Add figure-block CSS if not present
    if (-not ($noteContent -match 'figure-block')) {
        $cssBlock = @"
<style>
.figure-block { margin: 20px 0; text-align: center; }
.figure-block img { max-width: 100%; border-radius: 8px; border: 1px solid #333; }
.figure-block .caption { color: #aaa; font-size: 0.85em; margin-top: 8px; text-align: left; padding: 0 10px; }
</style>
"@
        if ($noteContent -match '</head>') {
            $noteContent = $noteContent -replace '</head>', "$cssBlock</head>"
        }
    }
    
    Set-Content $noteFile -Value $noteContent -Encoding UTF8
    Write-Output "Updated: $($paper.noteFile) with $($paper.figures.Count) figures"
}

Write-Output "`nAll notes updated!"
