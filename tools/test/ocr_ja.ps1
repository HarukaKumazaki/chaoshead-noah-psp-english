# Japanese OCR (Windows.Media.Ocr) over every PNG in a folder; writes "name<TAB>text" lines to a UTF-8 file.
# usage: powershell -File ocr_ja.ps1 <folder> <out.tsv>
param([string]$Dir, [string]$Out)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(); $task.Result }
$lang = New-Object Windows.Globalization.Language 'ja'
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$w = New-Object System.IO.StreamWriter($Out, $false, (New-Object System.Text.UTF8Encoding $false))
$files = Get-ChildItem -LiteralPath $Dir -Filter *.png
$i = 0
foreach ($f in $files) {
    $i++
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
        $txt = ($res.Lines | ForEach-Object { $_.Text }) -join ' / '
        $stream.Dispose()
        $w.WriteLine($f.BaseName + "`t" + $txt)
    } catch { $w.WriteLine($f.BaseName + "`tERROR " + $_.Exception.Message) }
    if ($i % 500 -eq 0) { $w.Flush(); Write-Host "$i / $($files.Count)" }
}
$w.Close()
Write-Host "done $i"
