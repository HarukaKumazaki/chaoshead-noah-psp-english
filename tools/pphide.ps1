# Park the PPSSPP window off-screen without activating it, so tests run in the background.
Add-Type @"
using System; using System.Runtime.InteropServices;
public class H {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
}
"@
for ($i = 0; $i -lt 100; $i++) {
  $p = Get-Process PPSSPPWindows64 -ErrorAction SilentlyContinue | ? { $_.MainWindowHandle -ne 0 } | Select -First 1
  if ($p) { break }
  Start-Sleep -Milliseconds 200
}
if (-not $p) { exit 1 }
$h = $p.MainWindowHandle
[H]::ShowWindow($h, 4) | Out-Null                       # SW_SHOWNOACTIVATE (un-minimize, no focus)
# HWND_BOTTOM, far off-screen, 960x544 client-ish size; SWP_NOACTIVATE
[H]::SetWindowPos($h, [IntPtr]1, -5000, -5000, 976, 583, 0x0010) | Out-Null
"hidden $h"
