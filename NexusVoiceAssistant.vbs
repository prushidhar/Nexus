Set WshShell = CreateObject("WScript.Shell")
pythonExe = "C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\runtime\python\python.exe"
daemonScript = "C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\laptop\nexus_daemon.py"
cmdLine = """" & pythonExe & """ -u """ & daemonScript & """"
WshShell.Run cmdLine, 0, False
