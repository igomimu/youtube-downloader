$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\lucky\Desktop\TubeDownloader.lnk")
$Shortcut.TargetPath = "C:\Users\lucky\Desktop\TubeDownloader.bat"
$Shortcut.IconLocation = "C:\Users\lucky\Desktop\TubeDownloader.ico"
$Shortcut.WindowStyle = 7 
# 7 = Minimized (starts minimized if possible, but for batch it might still show briefly)
# Actually, let's keep it normal (1) or just default
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "Shortcut created"
