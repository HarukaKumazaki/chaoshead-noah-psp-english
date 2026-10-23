# CHAOS;HEAD NOAH (PSP) English patcher for Windows (Windows PowerShell 5.1+, nothing to install).
# Run through Patch-Windows.bat: double-click it and pick the ISO, or drag the ISO onto it.
# Needs only the Japanese ISO and ChaosHeadNoah_PSP_EN.dat next to this script (no PC/Steam copy of the game).
# The original ISO is never modified; the English ISO is written as a new file.
param([string]$Iso, [string]$Out)
$ErrorActionPreference = 'Stop'
$Dat = Join-Path $PSScriptRoot 'ChaosHeadNoah_PSP_EN.dat'
$Sector = 2048
$Header = 128          # index sectors at the start of the .dat; data sector 0 follows them

function Fail($msg) { Write-Host ''; Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

function Get-Sha256([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
    try { return ([System.BitConverter]::ToString($sha.ComputeHash($fs)) -replace '-', '').ToLower() }
    finally { $fs.Dispose() }
}

if (-not $Iso) {
    Add-Type -AssemblyName System.Windows.Forms
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title = 'Select the original CHAOS;HEAD NOAH (Japan) PSP ISO'
    $dlg.Filter = 'PSP ISO (*.iso)|*.iso|All files (*.*)|*.*'
    if ($dlg.ShowDialog() -ne 'OK') { Fail 'No ISO selected.' }
    $Iso = $dlg.FileName
}
if (-not (Test-Path -LiteralPath $Iso)) { Fail "File not found: $Iso" }
$Iso = (Resolve-Path -LiteralPath $Iso).Path
if (-not $Out) {
    # never overwrite: an existing (maybe still open) English ISO gets a numbered sibling instead
    $dir = Split-Path $Iso; $Out = Join-Path $dir 'Chaos;Head Noah (English).iso'; $n = 2
    while ((Test-Path -LiteralPath $Out) -or ($Out -eq $Iso)) { $Out = Join-Path $dir "Chaos;Head Noah (English) ($n).iso"; $n++ }
}
if ($Out -eq $Iso) { Fail 'The output must be a different file from the original ISO.' }
if (-not (Test-Path -LiteralPath $Dat)) { Fail 'Keep this patcher next to ChaosHeadNoah_PSP_EN.dat.' }

$info = @{}; $blocks = @(); $results = @{}; $patched = @{}; $files = @()
$fs = [System.IO.File]::Open($Dat, 'Open', 'Read', 'Read')
$head = New-Object byte[] ($Header * $Sector)
try { $null = $fs.Read($head, 0, $head.Length) } finally { $fs.Dispose() }
foreach ($line in [System.Text.Encoding]::ASCII.GetString($head).Split("`n")) {
    if ($line -eq 'end') { break }
    $f = $line.Split(' ')
    if ($f[0] -eq 'copy') { $blocks += , @([int64]$f[1], [int64]$f[2], [int64]$f[3], 'copy') }
    elseif ($f[0] -eq 'block') { $blocks += , @([int64]$f[1], ([int64]$f[2] + $Header), [int64]$f[3], 'block') }
    elseif ($f[0] -eq 'variant') { $results[$f[1]] = $f[2] }          # other accepted dumps (e.g. PSN)
    elseif ($f[0] -eq 'patched') { $patched[$f[1]] = $f[2] }          # already-English ISOs
    elseif ($f[0] -eq 'file') { $files += , @($f[1], ([int64]$f[2] * $Sector), [int64]$f[3], ($f[4..($f.Count - 1)] -join ' ')) }
    elseif ($f.Count -eq 2) { $info[$f[0]] = $f[1] }
}

Write-Host 'Checking the original ISO (this takes a moment)...'
if (-not $info['size']) { Fail 'ChaosHeadNoah_PSP_EN.dat is damaged. Download it again.' }
$results[$info['source_sha256']] = $info['result_sha256']
if ((Get-Item -LiteralPath $Iso).Length -ne [int64]$info['size']) {
    Fail "This is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($($info['size']) bytes)."
}
$srcSha = Get-Sha256 $Iso
if ($patched.ContainsKey($srcSha)) {
    Fail "This ISO is already the English patch (version $($patched[$srcSha])). Patch your original Japanese ISO instead."
}
if (-not $results.ContainsKey($srcSha)) {
    Fail "This is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($($info['size']) bytes)."
}
$info['result_sha256'] = $results[$srcSha]
Write-Host 'Copying...'
try { [System.IO.File]::Copy($Iso, $Out, $true) }
catch { Fail "Cannot write $Out (is it open in an emulator or another program?). Close it or pick another output name." }
Write-Host "Patching ($($blocks.Count) steps)..."
# copy: sectors taken from the original ISO; block: new sectors from the .dat
$bin = $null; $orig = $null; $dst = $null
try {
    $bin = [System.IO.File]::Open($Dat, 'Open', 'Read', 'Read')
    $orig = [System.IO.File]::Open($Iso, 'Open', 'Read', 'Read')
    $dst = [System.IO.File]::Open($Out, 'Open', 'ReadWrite', 'None')
    $buf = New-Object byte[] (1MB)
    foreach ($b in $blocks) {
        if ($b[3] -eq 'copy') { $src = $orig } else { $src = $bin }
        $src.Seek($b[1] * $Sector, 'Begin') | Out-Null
        $dst.Seek($b[0] * $Sector, 'Begin') | Out-Null
        $left = $b[2] * $Sector
        while ($left -gt 0) {
            $n = $src.Read($buf, 0, [int][Math]::Min($buf.Length, $left))
            if ($n -le 0) { Fail 'The patch file is damaged. Download it again.' }
            $dst.Write($buf, 0, $n)
            $left -= $n
        }
    }
} finally {                       # always release the files, also after an error
    foreach ($h in @($bin, $orig, $dst)) { if ($h) { $h.Dispose() } }
}

# one pass over the output: the whole image and every patched file at its place in it
Write-Host "Checking every patched file and the whole ISO..."
$files = @($files | Sort-Object { $_[1] })
$whole = [System.Security.Cryptography.SHA256]::Create()
$fileSha = @($files | ForEach-Object { [System.Security.Cryptography.SHA256]::Create() })
$fs = [System.IO.File]::Open($Out, 'Open', 'Read', 'ReadWrite')
try {
    $buf = New-Object byte[] (4MB); $pos = [int64]0; $next = 0
    while (($n = $fs.Read($buf, 0, $buf.Length)) -gt 0) {
        $null = $whole.TransformBlock($buf, 0, $n, $null, 0)
        $end = $pos + $n
        for ($j = $next; $j -lt $files.Count -and $files[$j][1] -lt $end; $j++) {
            $a = [Math]::Max($files[$j][1], $pos); $z = [Math]::Min($files[$j][1] + $files[$j][2], $end)
            if ($z -gt $a) { $null = $fileSha[$j].TransformBlock($buf, [int]($a - $pos), [int]($z - $a), $null, 0) }
        }
        while ($next -lt $files.Count -and $files[$next][1] + $files[$next][2] -le $end) { $next++ }
        $pos = $end
    }
} finally { $fs.Dispose() }
$bad = 0
for ($j = 0; $j -lt $files.Count; $j++) {
    $null = $fileSha[$j].TransformFinalBlock((New-Object byte[] 0), 0, 0)
    $got = ([System.BitConverter]::ToString($fileSha[$j].Hash) -replace '-', '').ToLower()
    $label = "$($files[$j][3]) ($('{0:N0}' -f $files[$j][2]) bytes)"
    if ($got -eq $files[$j][0]) { Write-Host "  [OK]   $label" -ForegroundColor Green }
    else { Write-Host "  [FAIL] $label" -ForegroundColor Red; $bad++ }
}
$null = $whole.TransformFinalBlock((New-Object byte[] 0), 0, 0)
$outSha = ([System.BitConverter]::ToString($whole.Hash) -replace '-', '').ToLower()
if ($bad -or $outSha -ne $info['result_sha256']) { Fail 'Verification failed: delete the output file and try again.' }
Write-Host ''
Write-Host 'Check passed: 100% patched.' -ForegroundColor Green
Write-Host "  $($files.Count) of $($files.Count) patched files verified, each in its correct place"
Write-Host "  every byte ($('{0:N0}' -f $pos)) of the ISO matches the expected English ISO"
Write-Host "  SHA-256 $outSha"
Write-Host ''
Write-Host "Done: $Out" -ForegroundColor Green
