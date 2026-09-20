' CodeTutor 守护进程启动器(无窗口)
Set ws = CreateObject("Wscript.Shell")
ws.Run "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Users\nujidetiejiang\Desktop\智能体\codetutor\watchdog.ps1""", 0, False
