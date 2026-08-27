Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 1. 관리자 권한이 없으면 관리자 권한으로 자동 재실행
If Not WScript.Arguments.Named.Exists("elevated") Then
    CreateObject("Shell.Application").ShellExecute "wscript.exe", """" & WScript.ScriptFullName & """ /elevated", currentDir, "runas", 0
    WScript.Quit
End If

WshShell.CurrentDirectory = currentDir

' 2. 기존 실행 중인 main_app 서버 정리
On Error Resume Next
WshShell.Run "taskkill /f /im pythonw.exe", 0, True
On Error Goto 0

' 3. 파이썬 웹서버 백그라운드 완전 숨김 구동 (pythonw.exe)
WshShell.Run """.venv\Scripts\pythonw.exe"" main_app.py", 0, False

WScript.Sleep 1200

' 4. 구글 크롬으로 127.0.0.1:15874 단독 오픈
chromeFound = False
chromePaths = Array(_
    "C:\Program Files\Google\Chrome\Application\chrome.exe",_
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",_
    WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")_
)

For Each cp In chromePaths
    If fso.FileExists(cp) Then
        WshShell.Run """" & cp & """ http://127.0.0.1:15874", 1, False
        chromeFound = True
        Exit For
    End If
Next

If Not chromeFound Then
    WshShell.Run "http://127.0.0.1:15874", 1, False
End If