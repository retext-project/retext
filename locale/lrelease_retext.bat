@echo off
:: Enable delayed expansion, so the variable (tspath, qmpath) 
:: in for-loop can be updated in real-time. 
SETLOCAL ENABLEDELAYEDEXPANSION 
for /r ./ %%i in (*.ts) do (
	set tspath=%%i
	set qmpath=!tspath:~0,-2!qm 
	::if not exist *.qm files, lrelease *.ts to *.qm
	if not exist !qmpath! lrelease !tspath!
	)