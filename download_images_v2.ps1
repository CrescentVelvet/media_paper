# Corrected batch download script
# Key fix: image URLs need version-aware path construction

$papers = @(
    @{id="2503.11651"; ver="2503.11651v1"; file="3D-20250314-VGGT"; maxImgs=5},
    @{id="2412.01506"; ver="2412.01506"; file="3D-20241202-TRELLIS"; maxImgs=6},
    @{id="2501.12202"; ver="2501.12202"; file="3D-20250121-Hunyuan3D"; maxImgs=5},
    @{id="2311.06214"; ver="2311.06214"; file="3D-20231110-FeedForward-Reconstruction"; maxImgs=5},
    @{id="2605.16355"; ver="2605.16355"; file="3D-20260508-TripoSplat"; maxImgs=5},
    @{id="2310.12190"; ver="2310.12190v1"; file="VideoGen-20231018-DynamiCrafter"; maxImgs=4},
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
$imgDir = "C:\code\media_paper\images"
$htmlDir = "C:\code\media_paper\html_src"

# Try multiple version paths for each paper
foreach ($p in $papers) {
    $paperImgDir = Join-Path $imgDir $p.id
    if (-not (Test-Path $paperImgDir)) { New-Item -ItemType Directory -Path $paperImgDir -Force | Out-Null }
    
    # Find the HTML file
    $htmlFile = Get-ChildItem $htmlDir -Filter "$($p.ver)*.html" | Select-Object -First 1
    if (-not $htmlFile) {
        # Try without version
        $htmlFile = Get-ChildItem $htmlDir -Filter "$($p.id)*.html" | Select-Object -First 1
    }
    if (-not $htmlFile) {
        Write-Output "HTML not found: $($p.id)"
        continue
    }
    
    $html = Get-Content $htmlFile.FullName -Raw
    
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
        Write-Output "$($p.id): NO images found in HTML"
        continue
    }
    
    # Determine the correct base path for images
    # The HTML file name tells us the version (e.g., 2503.11651v1.html means images at 2503.11651v1/)
    $htmlBaseName = $htmlFile.BaseName  # e.g., "2503.11651v1" or "2503.11651"
    
    $downloaded = 0
    $imgInfo = @()
    $maxCount = [Math]::Min($p.maxImgs, $imgs.Count)
    
    for ($i = 0; $i -lt $maxCount; $i++) {
        $src = $imgs[$i]
        
        # Construct full URL based on path type
        if ($src -match '^https?://') {
            $fullUrl = $src
        } elseif ($src -match '^(\d{4}\.\d{4,5}v?\d*)/') {
            # Path already has version prefix (e.g., "2501.12202v5/x1.png")
            $fullUrl = $baseUrl + $src
        } elseif ($src -match '^extracted/') {
            # Extracted path - needs full version prefix
            $fullUrl = $baseUrl + "$htmlBaseName/" + $src
        } else {
            # Relative path like "x1.png" - prepend version path
            $fullUrl = $baseUrl + "$htmlBaseName/" + $src
        }
        
        $ext = [System.IO.Path]::GetExtension($src)
        $localName = "fig$($i+1)$ext"
        $localPath = Join-Path $paperImgDir $localName
        
        try {
            $wc = New-Object System.Net.WebClient
            $wc.Headers.Add("User-Agent", "Mozilla/5.0")
            $wc.DownloadFile($fullUrl, $localPath)
            $size = (Get-Item $localPath).Length
            if ($size -gt 100) {
                $cap = if ($i -lt $caps.Count) { $caps[$i] } else { "" }
                if ($cap.Length -gt 250) { $cap = $cap.Substring(0, 250) + "..." }
                $imgInfo += [PSCustomObject]@{ idx=$i; file=$localName; size=$size; caption=$cap; url=$fullUrl }
                $downloaded++
                Write-Output "  OK $($p.id) fig$($i+1): $size bytes"
            } else {
                Remove-Item $localPath -ErrorAction SilentlyContinue
                Write-Output "  SKIP $($p.id) fig$($i+1): too small ($size bytes)"
            }
            $wc.Dispose()
        } catch {
            Write-Output "  FAIL $($p.id) fig$($i+1): $($_.Exception.Message)"
            # Try alternative URL without version
            if ($src -notmatch '^https?://' -and $src -notmatch '^extracted/') {
                $altUrl = $baseUrl + "$($p.id)/" + $src
                try {
                    $wc2 = New-Object System.Net.WebClient
                    $wc2.Headers.Add("User-Agent", "Mozilla/5.0")
                    $wc2.DownloadFile($altUrl, $localPath)
                    $size = (Get-Item $localPath).Length
                    if ($size -gt 100) {
                        $cap = if ($i -lt $caps.Count) { $caps[$i] } else { "" }
                        if ($cap.Length -gt 250) { $cap = $cap.Substring(0, 250) + "..." }
                        $imgInfo += [PSCustomObject]@{ idx=$i; file=$localName; size=$size; caption=$cap; url=$altUrl }
                        $downloaded++
                        Write-Output "  OK(alt) $($p.id) fig$($i+1): $size bytes"
                    }
                    $wc2.Dispose()
                } catch {
                    Write-Output "  FAIL(alt) $($p.id) fig$($i+1): $($_.Exception.Message)"
                }
            }
        }
    }
    
    Write-OUTPUT "$($p.id) ($($p.file)): $downloaded/$maxCount images downloaded"
    
    # Save image info as JSON
    if ($imgInfo.Count -gt 0) {
        $infoFile = Join-Path $paperImgDir "info.json"
        $imgInfo | ConvertTo-Json -Depth 2 | Out-File $infoFile -Encoding UTF8
    }
}

Write-Output "`nDone!"
