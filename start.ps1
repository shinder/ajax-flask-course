# 啟動 Flask 開發伺服器（uv run flask run）
#
# Windows PowerShell 預設執行原則為 Restricted，直接執行 .\start.ps1 會出現
# 「因為這個系統上已停用指令碼執行」的錯誤。兩種解法擇一：
#
#   1. 只放寬這一次（不改系統設定）：
#        powershell -ExecutionPolicy Bypass -File .\start.ps1
#
#   2. 一次設定、之後都能執行（只影響目前使用者，不需要系統管理員）：
#        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#      設定後直接 .\start.ps1 即可。
#
# 若檔案是從網路下載（例如 zip 解壓），RemoteSigned 仍會擋，先解除封鎖：
#        Unblock-File .\start.ps1
#
# 不想碰執行原則的話，改用 .\start.bat 也可以，.bat 不受執行原則限制。

# 以腳本所在位置為基準，不管在哪個目錄執行都能找到專案
Push-Location $PSScriptRoot
try {
    uv run flask run
}
finally {
    # 不論正常結束或 Ctrl+C 中斷，都回到原本的目錄
    Pop-Location
}
