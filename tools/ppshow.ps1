# Show the PPSSPP window on screen (top-left, 2x size) without giving it keyboard focus,
# so the tests stay watchable while input keeps going through the debugger API only.
Add-Type @"
using System; using System.Runtime.InteropServices;
public class S {
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
[S]::ShowWindow($h, 4) | Out-Null                       # SW_SHOWNOACTIVATE
# HWND_TOP, on screen at (60,60), 960x544 client-ish; SWP_NOACTIVATE
[S]::SetWindowPos($h, [IntPtr]0, 60, 60, 976, 583, 0x0010) | Out-Null
"shown $h"
