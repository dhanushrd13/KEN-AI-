Option Explicit
Dim shell, fso, folder, shortcut
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set shortcut = shell.CreateShortcut(shell.SpecialFolders("Desktop") & "\KEN AI.lnk")
shortcut.TargetPath = folder & "\run.bat"
shortcut.WorkingDirectory = folder
shortcut.IconLocation = folder & "\kenai.ico,0"
shortcut.Description = "Open KEN AI NEXT GEN"
shortcut.Save
