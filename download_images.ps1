# Batch download key images from arXiv HTML and update notes
# For each paper: download first 5 images (architecture/algorithm figures + result comparisons)

$papers = @(
    @{id="2503.11651"; file="3D-20250314-VGGT"; htmlVer="2503.11651"; maxImgs=5},
    @{id="2412.01506"; file="3D-20241202-TRELLIS"; htmlVer="2412.01506"; maxImgs=6},
    @{id="2501.12202"; file="3D-20250121-Hunyuan3D"; htmlVer="2501.12202v5"; maxImgs=5},
    @{id="2311.06214"; file="3D-20231110-FeedForward-Reconstruction"; htmlVer="2311.06214"; maxImgs=5},
    @{id="2605.16355"; file="3D-20260508-TripoSplat"; htmlVer="2605.16355v1"; maxImgs=5},
    @{id="2309.16653"; file="3D-20230928-3D-Generation-Gaussian"; htmlVer="2309.16653"; maxImgs=0},
    @{id="2309.13101"; file="3D-20230922-Deformable-3DGS"; htmlVer="2309.13101v1"; maxImgs=0},
    @{id="2310.12190"; file="VideoGen-20231018-DynamiCrafter"; htmlVer="2310.12190v1"; maxImgs=4},
    @{id="2501.00103"; file="VideoGen-20241230-LTX"; htmlVer="2501.00103"; maxImgs=6},
    @{id="2503.07598"; file="VideoGen-20250310-VACE"; htmlVer="2503.07598"; maxImgs=4},
    @{id="2603.05503"; file="VideoGen-20241015-Mochi1"; htmlVer="2603.05503v1"; maxImgs=3},
    @{id="2506.19774"; file="VideoGen-20250620-Kling2"; htmlVer="2506.19774"; maxImgs=4},
    @{id="2511.14993"; file="VideoGen-20251119-Kandinsky5"; htmlVer="2511.14993v3"; maxImgs=5},
    @{id="2511.18870"; file="VideoGen-20251124-HunyuanVideo1.5"; htmlVer="2511.18870"; maxImgs=3},
    @{id="2512.08765"; file="VideoGen-20251209-Wan-Move"; htmlVer="2512.08765"; maxImgs=4},
    @{id="2603.27866"; file="VideoGen-20260329-Wan-R1"; htmlVer="2603.27866v1"; maxImgs=4},
    @{id="2604.24764"; file="VideoGen-20260427-GeometricConsistency"; htmlVer="2604.24764v4"; maxImgs=4},
    @{id="2606.20774"; file="VideoGen-20260618-CameraControl"; htmlVer="2606.20774"; maxImgs=4},
    @{id="2606.25041"; file="VideoGen-20260623-Wan-Streamer"; htmlVer="2606.25041"; maxImgs=4}
)

$wc = New-Object System.Net.WebClient
$wc.Headers.Add("User-Agent", "Mozilla/5.0")

$baseUrl = "https://arxiv.org/html/"
$imgDir = "C:\code\media_paper\images"

foreach ($p in $papers) {
    if ($p.maxImgs -eq 0) {
        Write-Output "SKIP $($p.id) ($($p.file)) - no images in HTML"
        continue
    }
    
    $paperImgDir = Join-Path $imgDir $p.id
    if (-not (Test-Path $paperImgDir)) { New-Item -ItemType Directory -Path $paperImgDir -Force | Out-Null }
    
    # Read HTML source
    $htmlFile = "C:\code\media_paper\html_src\$($p.htmlVer).html"
    if (-not (Test-Path $htmlFile)) {
        Write-Output "HTML not found for $($p.id): $htmlFile"
        continue
    }
    
    $html = Get-Content $htmlFile -Raw
    
    # Extract image srcs (filter out arxiv-logo and browse paths)
    $imgMatches = [regex]::Matches($html, 'src="([^"]*\.(?:png|jpg|gif))"')
    $imgs = @()
    foreach ($m in $imgMatches) {
        $src = $m.Groups[1].Value
        if ($src -notmatch 'arxiv-logo' -and $src -notmatch 'browse' -and $src -notmatch 'static') {
            $imgs += $src
        }
    }
    
    # Extract figure captions
    $capMatches = [regex]::Matches($html, '<figcaption[^>]*>(.*?)</figcaption>', 'Singleline')
    $caps = @()
    foreach ($m in $capMatches) {
        $text = $m.Groups[1].Value -replace '<[^>]+>', '' -replace '\s+', ' '
        $caps += $text.Trim()
    }
    
    # Download first N images
    $downloaded = 0
    $imgInfo = @()
    
    for ($i = 0; $i -lt [Math]::Min($p.maxImgs, $imgs.Count); $i++) {
        $src = $imgs[$i]
        # Construct full URL
        if ($src -match '^https?://') {
            $fullUrl = $src
        } else {
            $fullUrl = $baseUrl + $src
        }
        
        # Determine local filename
        $ext = [System.IO.Path]::GetExtension($src)
        $localName = "fig$($i+1)$ext"
        $localPath = Join-Path $paperImgDir $localName
        
        try {
            $wc.DownloadFile($fullUrl, $localPath)
            $size = (Get-Item $localPath).Length
            if ($size -gt 0) {
                $cap = if ($i -lt $caps.Count) { $caps[$i] } else { "" }
                # Truncate caption to 200 chars
                if ($cap.Length -gt 200) { $cap = $cap.Substring(0, 200) + "..." }
                $imgInfo += [PSCustomObject]@{ idx=$i; file=$localName; size=$size; caption=$cap; src=$src }
                $downloaded++
                Write-Output "  $($p.id) fig$($i+1): $size bytes"
            } else {
                Remove-Item $localPath -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Output "  $($p.id) fig$($i+1): FAILED - $($_.Exception.Message)"
        }
    }
    
    Write-Output "$($p.id) ($($p.file)): $downloaded/$($p.maxImgs) images downloaded"
    
    # Save image info as JSON for later use in updating HTML notes
    $infoFile = Join-Path $paperImgDir "info.json"
    $imgInfo | ConvertTo-Json -Depth 2 | Out-File $infoFile -Encoding UTF8
}

$wc.Dispose()
Write-Output "`nDone! All images downloaded."
