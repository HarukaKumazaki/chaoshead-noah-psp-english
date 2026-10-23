# PPSSPP test helper.
#   pp.ps1 shot <out.png>                 capture the PPSSPP window
#   (input is sent through ppdbg.py, never as keystrokes)
param([string]$cmd, [string]$a, [int]$count = 1, [int]$hold = 80)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
}
"@
[W]::SetProcessDPIAware() | Out-Null
$p = Get-Process PPSSPPWindows64 -ErrorAction Stop | Select-Object -First 1
$h = $p.MainWindowHandle
if ($cmd -eq 'shot') {
  if ([W]::IsIconic($h)) {
    [W]::ShowWindow($h, 4) | Out-Null   # restore without activating
    [W]::SetWindowPos($h, [IntPtr]1, -5000, -5000, 1000, 600, 0x0010) | Out-Null
    Start-Sleep -Milliseconds 500
  }
  $r = New-Object W+RECT; [W]::GetClientRect($h, [ref]$r) | Out-Null
  $pt = New-Object W+POINT; [W]::ClientToScreen($h, [ref]$pt) | Out-Null
  $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc(); [W]::PrintWindow($h, $hdc, 3) | Out-Null; $g.ReleaseHdc($hdc)
  $bmp.Save($a, [System.Drawing.Imaging.ImageFormat]::Png)
  "saved $a $($bmp.Width)x$($bmp.Height)"
}
