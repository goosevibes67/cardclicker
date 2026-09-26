Option Explicit

Dim shell, files, folder, appPath, link
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
appPath = files.BuildPath(folder, "NoPixel Giveaway Clicker.exe")

If Not files.FileExists(appPath) Then
    MsgBox "NoPixel Giveaway Clicker.exe is missing. Extract the whole ZIP first.", vbExclamation, "Card Clicker"
    WScript.Quit 1
End If

Set link = shell.CreateShortcut(files.BuildPath(folder, "NoPixel Giveaway Clicker.lnk"))
link.TargetPath = appPath
link.WorkingDirectory = folder
link.Description = "Launch NoPixel Giveaway Clicker"
link.IconLocation = appPath & ",0"
link.Save
MsgBox "Shortcut created. Drag NoPixel Giveaway Clicker.lnk to your Desktop.", vbInformation, "Card Clicker"
