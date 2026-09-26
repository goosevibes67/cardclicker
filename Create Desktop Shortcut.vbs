Option Explicit

Dim shell, files, folder, appPath, link
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
appPath = files.BuildPath(folder, "Auto Clicker.exe")

If Not files.FileExists(appPath) Then
    MsgBox "Auto Clicker.exe is missing. Extract the whole ZIP first.", vbExclamation, "Auto Clicker"
    WScript.Quit 1
End If

Set link = shell.CreateShortcut(files.BuildPath(folder, "Auto Clicker.lnk"))
link.TargetPath = appPath
link.WorkingDirectory = folder
link.Description = "Launch the Auto Clicker"
link.IconLocation = appPath & ",0"
link.Save
MsgBox "Shortcut created. Drag Auto Clicker.lnk to your Desktop.", vbInformation, "Auto Clicker"
