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
    $fs = [System.IO.File]::OpenRead($path)
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
if (-not $Out) { $Out = Join-Path (Split-Path $Iso) 'Chaos;Head Noah (English).iso' }
if ($Out -eq $Iso) { Fail 'The output must be a different file from the original ISO.' }
if (-not (Test-Path -LiteralPath $Dat)) { Fail 'Keep this patcher next to ChaosHeadNoah_PSP_EN.dat.' }

$info = @{}; $blocks = @()
$fs = [System.IO.File]::OpenRead($Dat)
$head = New-Object byte[] ($Header * $Sector)
$null = $fs.Read($head, 0, $head.Length); $fs.Dispose()
foreach ($line in [System.Text.Encoding]::ASCII.GetString($head).Split("`n")) {
    if ($line -eq 'end') { break }
    $f = $line.Split(' ')
    if ($f[0] -eq 'copy') { $blocks += , @([int64]$f[1], [int64]$f[2], [int64]$f[3], 'copy') }
    elseif ($f[0] -eq 'block') { $blocks += , @([int64]$f[1], ([int64]$f[2] + $Header), [int64]$f[3], 'block') }
    elseif ($f.Count -eq 2) { $info[$f[0]] = $f[1] }
}

Write-Host 'Checking the original ISO (this takes a moment)...'
if (-not $info['size']) { Fail 'ChaosHeadNoah_PSP_EN.dat is damaged. Download it again.' }
if ((Get-Item -LiteralPath $Iso).Length -ne [int64]$info['size'] -or (Get-Sha256 $Iso) -ne $info['source_sha256']) {
    Fail "This is not the expected ISO: CHAOS;HEAD NOAH (Japan) ULJM05692, unmodified ($($info['size']) bytes)."
}
Write-Host 'Copying...'
Copy-Item -LiteralPath $Iso -Destination $Out -Force
Write-Host "Patching ($($blocks.Count) steps)..."
# copy: sectors taken from the original ISO; block: new sectors from the .dat
$bin = [System.IO.File]::OpenRead($Dat)
$orig = [System.IO.File]::OpenRead($Iso)
$dst = [System.IO.File]::Open($Out, 'Open', 'ReadWrite')
try {
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
} finally { $bin.Dispose(); $orig.Dispose(); $dst.Dispose() }

Write-Host 'Verifying...'
if ((Get-Sha256 $Out) -ne $info['result_sha256']) { Fail 'Verification failed: delete the output file and try again.' }
Write-Host ''
Write-Host "Done: $Out" -ForegroundColor Green
