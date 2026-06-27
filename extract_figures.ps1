# Strategy: Instead of downloading images (too slow), 
# 1. Extract image URLs and captions from HTML source
# 2. Generate an "arxiv-figures.json" for each paper with online image URLs
# 3. Update HTML notes to embed online arXiv image URLs directly

$papers = @(
    @{id="2503.11651"; ver="2503.11651"; file="3D-20250314-VGGT"; maxImgs=5},
    @{id="2412.01506"; ver="2412.01506"; file="3D-20241202-TRELLIS"; maxImgs=6},
    @{id="2501.12202"; ver="2501.12202"; file="3D-20250121-Hunyuan3D"; maxImgs=5},
    @{id="2311.06214"; ver="2311.06214"; file="3D-20231110-FeedForward-Reconstruction"; maxImgs=5},
    @{id="2605.16355"; ver="2605.16355"; file="3D-20260508-TripoSplat"; maxImgs=5},
    @{id="2310.12190"; ver="2310.12190"; file="VideoGen-20231018-DynamiCrafter"; maxImgs=4},
    @{id="2501.00103"; ver="2501.00103"; file="VideoGen-20241230-LTX"; maxImgs=6},
    @{id="2503.07598"; ver="2503.07598"; file="VideoGen-20250310-VACE"; maxImgs=4},
    @{id="2603.05503"; ver="2603.05503"; file="VideoGen-20241015-Mochi1"; maxImgs=3},
    @{id="2506.19774"; ver="2506.19774"; file="VideoGen-20250620-Kling2"; maxImgs=4},
    @{id="2511.14993"; ver="2511.14993"; file="VideoGen-20251119-Kandinsky5"; maxImgs=5},
    @{id="2511.18870"; ver="2511.18870"; file="VideoGen-20251124-HunyuanVideo1.5"; maxImgs=3},
    @{id="2512.08765"; ver="2512.08765"; file="VideoGen-20251209-Wan-Move"; maxImgs=4},
    @{id="2603.27866"; ver="2603.27866"; file="VideoGen-20260329-Wan-R1"; maxImgs=4},
    @{id="2604.24764"; ver="2604.24764"; file="VideoGen-20260427-GeometricConsistency"; maxImgs=4},
    @{id="2606.20774"; ver="2606.20774"; file="VideoGen-20260618-CameraControl"; maxImgs=4},
    @{id="2606.25041"; ver="2606.25041"; file="VideoGen-20260623-Wan-Streamer"; maxImgs=4}
)

$baseUrl = "https://arxiv.org/html/"
$htmlDir = "C:\code\media_paper\html_src"
$figDir = "C:\code\media_paper\figures"

if (-not (Test-Path $figDir)) { New-Item -ItemType Directory -Path $figDir -Force | Out-Null }

$allPaperInfo = @()

foreach ($p in $papers) {
    # Find HTML file
    $htmlFile = Get-ChildItem $htmlDir -Filter "$($p.ver)*.html" | Select-Object -First 1
    if (-not $htmlFile) {
        $htmlFile = Get-ChildItem $htmlDir -Filter "$($p.id)*.html" | Select-Object -First 1
    }
    if (-not $htmlFile) {
        Write-Output "HTML not found: $($p.id)"
        continue
    }
    
    $html = Get-Content $htmlFile.FullName -Raw
    $htmlBase = $htmlFile.BaseName  # e.g. "2503.11651v1" or "2503.11651"
    
    # Extract image srcs
    $imgMatches = [regex]::Matches($html, 'src="([^"]*\.(?:png|jpg|gif))"')
    $imgs = @()
    foreach ($m in $imgMatches) {
        $src = $m.Groups[1].Value
        if ($src -notmatch 'arxiv-logo' -and $src -notmatch 'browse' -and $src -notmatch 'static') {
            $imgs += $src
        }
    }
    
    # Extract captions
    $capMatches = [regex]::Matches($html, '<figcaption[^>]*>(.*?)</figcaption>', 'Singleline')
    $caps = @()
    foreach ($m in $capMatches) {
        $text = $m.Groups[1].Value -replace '<[^>]+>', '' -replace '\s+', ' '
        $caps += $text.Trim()
    }
    
    if ($imgs.Count -eq 0) {
        Write-Output "$($p.id): NO images in HTML"
        continue
    }
    
    # Build figure info with full URLs
    $figInfo = @()
    $maxCount = [Math]::Min($p.maxImgs, $imgs.Count)
    
    for ($i = 0; $i -lt $maxCount; $i++) {
        $src = $imgs[$i]
        
        # Construct full URL
        if ($src -match '^https?://') {
            $fullUrl = $src
        } elseif ($src -match '^(\d{4}\.\d{4,5}v?\d*)/') {
            $fullUrl = $baseUrl + $src
        } else {
            $fullUrl = $baseUrl + "$htmlBase/" + $src
        }
        
        $cap = if ($i -lt $caps.Count) { $caps[$i] } else { "" }
        if ($cap.Length -gt 300) { $cap = $cap.Substring(0, 300) + "..." }
        
        $figInfo += [PSCustomObject]@{
            figure = "Figure $($i+1)"
            url = $fullUrl
            caption = $cap
        }
    }
    
    # Save per-paper JSON
    $paperJson = [PSCustomObject]@{
        arxivId = $p.id
        noteFile = "$($p.file).html"
        figures = $figInfo
    }
    
    $jsonFile = Join-Path $figDir "$($p.id).json"
    $paperJson | ConvertTo-Json -Depth 3 | Out-File $jsonFile -Encoding UTF8
    
    Write-Output "$($p.id) ($($p.file)): $($figInfo.Count) figures extracted"
    foreach ($f in $figInfo) {
        Write-Output "  $($f.figure): $($f.caption.Substring(0, [Math]::Min(80, $f.caption.Length)))..."
    }
    
    $allPaperInfo += $paperJson
}

# Save combined JSON
$combinedFile = Join-Path $figDir "all_papers_figures.json"
$allPaperInfo | ConvertTo-Json -Depth 3 | Out-File $combinedFile -Encoding UTF8

Write-Output "`nTotal: $($allPaperInfo.Count) papers processed"
Write-Output "Combined JSON: $combinedFile"
